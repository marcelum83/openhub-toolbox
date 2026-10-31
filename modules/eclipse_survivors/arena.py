"""
Eclipse Survivors - 2D Action Roguelite Arena Widget
Handles 60 FPS rendering, camera tracking, sliding station doors, line-of-sight raycasting,
wall projectile collisions, solid enemy-enemy separation physics, doorway navigation AI,
and tactical transhuman combat.
"""
import math
import random
import heapq
from typing import List, Tuple, Optional, Set
from kivy.uix.widget import Widget
from kivy.graphics import Color, Rectangle, RoundedRectangle, Line, Ellipse
from kivy.metrics import dp, sp
from kivy.clock import Clock
from kivy.core.window import Window

try:
    from game_state import GameWorld, Enemy, Projectile, XPCore, SupplyCrate, Wall, StationDoor, StationRoom, KeycardPickup, StationTerminal, StationNPC
except ImportError:
    from .game_state import GameWorld, Enemy, Projectile, XPCore, SupplyCrate, Wall, StationDoor, StationRoom, KeycardPickup, StationTerminal, StationNPC


# --- Precomputed Station Waypoint Navigation Graph ---
WAYPOINT_NODES = {
    'airlock_center': (0.0, -820.0),
    'door_airlock': (0.0, -710.0),
    'conduit_mid': (0.0, -610.0),
    'prom_south': (0.0, -480.0),
    'prom_center': (0.0, -320.0),
    'prom_north_lane': (0.0, -200.0),
    'prom_south_lane': (0.0, -420.0),
    'prom_west_n': (-260.0, -200.0),
    'prom_west_s': (-260.0, -420.0),
    'prom_east_n': (260.0, -200.0),
    'prom_east_s': (260.0, -420.0),
    'door_prom_west': (-450.0, -310.0),
    'cryo_center': (-710.0, -310.0),
    'door_prom_east': (450.0, -310.0),
    'hydro_center': (710.0, -310.0),
    'door_prom_north': (0.0, -130.0),
    'armory_corridor_mid': (0.0, -35.0),
    'door_armory_south': (0.0, 70.0),
    'armory_center': (0.0, 250.0),
    'door_armory_west': (-390.0, 250.0),
    'research_center': (-680.0, 300.0),
    'door_reactor_blast': (0.0, 450.0),
    'elevator_center': (0.0, 670.0),
}

WAYPOINT_EDGES = [
    ('airlock_center', 'door_airlock'),
    ('door_airlock', 'conduit_mid'),
    ('conduit_mid', 'prom_south'),
    ('prom_south', 'prom_south_lane'),
    ('prom_south', 'prom_center'),
    ('prom_south_lane', 'prom_west_s'),
    ('prom_south_lane', 'prom_east_s'),
    ('prom_west_s', 'door_prom_west'),
    ('prom_west_s', 'prom_west_n'),
    ('door_prom_west', 'prom_west_n'),
    ('door_prom_west', 'cryo_center'),
    ('prom_east_s', 'door_prom_east'),
    ('prom_east_s', 'prom_east_n'),
    ('door_prom_east', 'prom_east_n'),
    ('door_prom_east', 'hydro_center'),
    ('prom_west_n', 'prom_north_lane'),
    ('prom_east_n', 'prom_north_lane'),
    ('prom_north_lane', 'prom_center'),
    ('prom_north_lane', 'door_prom_north'),
    ('door_prom_north', 'armory_corridor_mid'),
    ('armory_corridor_mid', 'door_armory_south'),
    ('door_armory_south', 'armory_center'),
    ('armory_center', 'door_armory_west'),
    ('door_armory_west', 'research_center'),
    ('armory_center', 'door_reactor_blast'),
    ('door_reactor_blast', 'elevator_center'),
]

WAYPOINT_ADJ = {k: [] for k in WAYPOINT_NODES}
for u, v in WAYPOINT_EDGES:
    w = math.hypot(WAYPOINT_NODES[u][0] - WAYPOINT_NODES[v][0], WAYPOINT_NODES[u][1] - WAYPOINT_NODES[v][1])
    WAYPOINT_ADJ[u].append((v, w))
    WAYPOINT_ADJ[v].append((u, w))


def get_waypoint_path(start_x: float, start_y: float, goal_x: float, goal_y: float, locked_doors: Optional[Set[str]] = None) -> List[Tuple[float, float]]:
    if locked_doors is None:
        locked_doors = set()
    s_node = min(WAYPOINT_NODES.keys(), key=lambda k: math.hypot(start_x - WAYPOINT_NODES[k][0], start_y - WAYPOINT_NODES[k][1]))
    g_node = min(WAYPOINT_NODES.keys(), key=lambda k: math.hypot(goal_x - WAYPOINT_NODES[k][0], goal_y - WAYPOINT_NODES[k][1]))
    if s_node == g_node:
        return [WAYPOINT_NODES[g_node]]
    q = [(0, s_node, [s_node])]
    visited = {}
    while q:
        cost, cur, path = heapq.heappop(q)
        if cur in visited and visited[cur] <= cost:
            continue
        visited[cur] = cost
        if cur == g_node:
            return [WAYPOINT_NODES[n] for n in path]
        for nxt, weight in WAYPOINT_ADJ[cur]:
            if nxt in locked_doors:
                continue
            heapq.heappush(q, (cost + weight, nxt, path + [nxt]))
    return [(goal_x, goal_y)]


def intersect_segments(p0_x, p0_y, p1_x, p1_y, p2_x, p2_y, p3_x, p3_y) -> Optional[float]:
    s1_x = p1_x - p0_x
    s1_y = p1_y - p0_y
    s2_x = p3_x - p2_x
    s2_y = p3_y - p2_y
    denom = (-s2_x * s1_y + s1_x * s2_y)
    if abs(denom) < 1e-8:
        return None
    s = (-s1_y * (p0_x - p2_x) + s1_x * (p0_y - p2_y)) / denom
    t = ( s2_x * (p0_y - p2_y) - s2_y * (p0_x - p2_x)) / denom
    if 0.0 <= s <= 1.0 and 0.0 <= t <= 1.0:
        return t
    return None


def segment_intersects_box(x0, y0, x1, y1, rx, ry, rw, rh) -> Tuple[Optional[float], Optional[str]]:
    if max(x0, x1) < rx or min(x0, x1) > rx + rw:
        return None, None
    if max(y0, y1) < ry or min(y0, y1) > ry + rh:
        return None, None
    if rx <= x0 <= rx + rw and ry <= y0 <= ry + rh:
        return 0.0, 'inside'
    min_t = None
    hit_edge = None
    edges = [
        ('top', rx, ry + rh, rx + rw, ry + rh),
        ('bottom', rx, ry, rx + rw, ry),
        ('left', rx, ry, rx, ry + rh),
        ('right', rx + rw, ry, rx + rw, ry + rh),
    ]
    for edge_name, p2_x, p2_y, p3_x, p3_y in edges:
        t = intersect_segments(x0, y0, x1, y1, p2_x, p2_y, p3_x, p3_y)
        if t is not None:
            if min_t is None or t < min_t:
                min_t = t
                hit_edge = edge_name
    return min_t, hit_edge



class ActionArena(Widget):
    def __init__(self, world: GameWorld, on_level_up, on_game_over, on_floor_complete=None, on_npc_interact=None, host_api=None, **kwargs):
        super().__init__(**kwargs)
        self.world = world
        self.on_level_up = on_level_up
        self.on_game_over = on_game_over
        self.on_floor_complete = on_floor_complete
        self.on_npc_interact = on_npc_interact
        self.host = host_api

        # Input State
        self.keys_pressed = set()
        self.touch_stick_origin = None
        self.touch_stick_current = None
        self.joystick_vector = (0.0, 0.0)

        # Visual Effects State
        self.emp_visuals: List[dict] = []
        self.railgun_visuals: List[dict] = []
        self.chain_lightning_visuals: List[dict] = []
        self.sparks: List[dict] = []

        # Keyboard Bindings
        Window.bind(on_key_down=self._on_key_down, on_key_up=self._on_key_up)

        # 60 FPS Game Loop
        self.game_loop = Clock.schedule_interval(self.update, 1.0 / 60.0)

    # --- Keyboard Input ---

    def _on_key_down(self, window, key, scancode, codepoint, modifier):
        self.keys_pressed.add(key)
        # 'E' (key 101), Space (key 32), or Enter (key 13) to interact with active NPC
        if key in (101, 32, 13) and self.world.active_npc:
            if self.on_npc_interact:
                self.on_npc_interact(self.world.active_npc)

    def _on_key_up(self, window, key, scancode):
        if key in self.keys_pressed:
            self.keys_pressed.remove(key)

    # --- Touch Joystick Input ---

    def on_touch_down(self, touch):
        if not self.collide_point(*touch.pos):
            return super().on_touch_down(touch)

        if touch.x < self.x + self.width * 0.55:
            self.touch_stick_origin = (touch.x, touch.y)
            self.touch_stick_current = (touch.x, touch.y)
            self._update_joystick()
            return True
        else:
            cx, cy = self.center_x, self.center_y
            dx = touch.x - cx
            dy = touch.y - cy
            if math.hypot(dx, dy) > dp(20):
                angle = math.degrees(math.atan2(dy, dx))
                self.world.player.facing_angle = angle
            return True

    def on_touch_move(self, touch):
        if self.touch_stick_origin and touch.x < self.x + self.width * 0.65:
            self.touch_stick_current = (touch.x, touch.y)
            self._update_joystick()
            return True
        return super().on_touch_move(touch)

    def on_touch_up(self, touch):
        self.touch_stick_origin = None
        self.touch_stick_current = None
        self.joystick_vector = (0.0, 0.0)
        return super().on_touch_up(touch)

    def _update_joystick(self):
        if not self.touch_stick_origin or not self.touch_stick_current:
            self.joystick_vector = (0.0, 0.0)
            return

        ox, oy = self.touch_stick_origin
        cx, cy = self.touch_stick_current
        dx = cx - ox
        dy = cy - oy
        dist = math.hypot(dx, dy)
        max_dist = dp(50)

        if dist < dp(8):
            self.joystick_vector = (0.0, 0.0)
        else:
            norm = min(1.0, dist / max_dist)
            self.joystick_vector = (dx / dist * norm, dy / dist * norm)

    # --- Main Simulation Loop ---

    def update(self, dt: float):
        if self.world.is_paused or self.world.is_game_over:
            return

        dt = min(dt, 0.05)
        player = self.world.player

        # 1. Player Locomotion
        mv_x, mv_y = 0.0, 0.0
        if 119 in self.keys_pressed or 273 in self.keys_pressed: mv_y += 1.0  # W / Up
        if 115 in self.keys_pressed or 274 in self.keys_pressed: mv_y -= 1.0  # S / Down
        if 97 in self.keys_pressed or 276 in self.keys_pressed:  mv_x -= 1.0  # A / Left
        if 100 in self.keys_pressed or 275 in self.keys_pressed: mv_x += 1.0  # D / Right

        jx, jy = self.joystick_vector
        mv_x += jx
        mv_y += jy

        length = math.hypot(mv_x, mv_y)
        if length > 0.05:
            norm_x = mv_x / max(1.0, length)
            norm_y = mv_y / max(1.0, length)
            player.x += norm_x * player.speed * dt
            player.y += norm_y * player.speed * dt
            player.facing_angle = math.degrees(math.atan2(norm_y, norm_x))

        # Clamp inside station
        half_w = self.world.map.width / 2.0 - player.radius - 20
        half_h = self.world.map.height / 2.0 - player.radius - 20
        player.x = max(-half_w, min(half_w, player.x))
        player.y = max(-half_h, min(half_h, player.y))

        # 2. Doors State & Proximity Sliding
        self._update_doors(dt)

        # 3. Wall & Door Collisions for Player
        for wall in self.world.map.walls:
            self._resolve_circle_wall_collision(player, wall)
        for door in self.world.map.doors:
            if not door.is_open:
                self._resolve_circle_rect_collision(player, door.x, door.y, door.w, door.h)

        # 4. Station Floor Room Detection & Clearance
        self.world.update_floor_time(dt)
        self.world.update_room_states()

        # 5. Interactive Terminals & NPCs
        self._update_terminals(dt)
        self._update_npcs_proximity()

        # 6. Weapons & Cybernetic Evolutions (LOS raycasted)
        self._update_weapons(dt)

        # 7. Projectiles (Impacts walls & closed doors)
        self._update_projectiles(dt)

        # 8. Enemies AI (Doorway navigation & solid separation)
        self._update_enemies(dt)

        # 9. XP Cores & Keycard Collection
        self._update_xp_cores(dt)
        self._update_keycard_pickup()

        # 10. Visual Effects & Notifications
        self._update_visual_effects(dt)

        # 11. Canvas Redraw
        self.redraw()

    # --- Line-of-Sight & Raycasting Math ---

    def _segments_intersect(self, ax, ay, bx, by, cx, cy, dx, dy) -> bool:
        def ccw(x1, y1, x2, y2, x3, y3):
            return (y3 - y1) * (x2 - x1) > (y2 - y1) * (x3 - x1)
        return (ccw(ax, ay, cx, cy, dx, dy) != ccw(bx, by, cx, cy, dx, dy) and
                ccw(ax, ay, bx, by, cx, cy) != ccw(ax, ay, bx, by, dx, dy))

    def _line_intersects_rect(self, x1, y1, x2, y2, rx, ry, rw, rh) -> bool:
        # Bounding box quick reject
        if max(x1, x2) < rx or min(x1, x2) > rx + rw:
            return False
        if max(y1, y2) < ry or min(y1, y2) > ry + rh:
            return False
        if (rx <= x1 <= rx + rw and ry <= y1 <= ry + rh) or (rx <= x2 <= rx + rw and ry <= y2 <= ry + rh):
            return True
        return (self._segments_intersect(x1, y1, x2, y2, rx, ry, rx + rw, ry) or
                self._segments_intersect(x1, y1, x2, y2, rx, ry + rh, rx + rw, ry + rh) or
                self._segments_intersect(x1, y1, x2, y2, rx, ry, rx, ry + rh) or
                self._segments_intersect(x1, y1, x2, y2, rx + rw, ry, rx + rw, ry + rh))

    def _has_line_of_sight(self, x1, y1, x2, y2) -> bool:
        """Returns True if the line between (x1, y1) and (x2, y2) is unblocked by walls and closed doors."""
        for wall in self.world.map.walls:
            if self._line_intersects_rect(x1, y1, x2, y2, wall.x, wall.y, wall.w, wall.h):
                return False
        for door in self.world.map.doors:
            if not door.is_open:
                if self._line_intersects_rect(x1, y1, x2, y2, door.x, door.y, door.w, door.h):
                    return False
        return True

    # --- Collision Helpers ---

    def _resolve_circle_wall_collision(self, entity, wall: Wall) -> Optional[Tuple[float, float]]:
        return self._resolve_circle_rect_collision(entity, wall.x, wall.y, wall.w, wall.h)

    def _resolve_circle_rect_collision(self, entity, rx, ry, rw, rh) -> Optional[Tuple[float, float]]:
        closest_x = max(rx, min(entity.x, rx + rw))
        closest_y = max(ry, min(entity.y, ry + rh))
        dx = entity.x - closest_x
        dy = entity.y - closest_y
        dist = math.hypot(dx, dy)

        if dist <= 0.001:
            d_left = entity.x - rx
            d_right = (rx + rw) - entity.x
            d_bottom = entity.y - ry
            d_top = (ry + rh) - entity.y
            min_d = min(d_left, d_right, d_bottom, d_top)
            if min_d == d_left:
                entity.x = rx - entity.radius
                return (-1.0, 0.0)
            elif min_d == d_right:
                entity.x = rx + rw + entity.radius
                return (1.0, 0.0)
            elif min_d == d_bottom:
                entity.y = ry - entity.radius
                return (0.0, -1.0)
            else:
                entity.y = ry + rh + entity.radius
                return (0.0, 1.0)

        if dist < entity.radius:
            overlap = entity.radius - dist
            nx = dx / dist
            ny = dy / dist
            entity.x += nx * overlap
            entity.y += ny * overlap
            return (nx, ny)

        return None

    # --- Doors Logic ---

    def _update_doors(self, dt: float):
        player = self.world.player

        for door in self.world.map.doors:
            dcx = door.x + door.w / 2.0
            dcy = door.y + door.h / 2.0
            dist_player = math.hypot(player.x - dcx, player.y - dcy)

            # Check if any enemy is also near the door (if door is unlocked)
            hostile_near = False
            if not door.is_locked:
                for enemy in self.world.enemies:
                    if math.hypot(enemy.x - dcx, enemy.y - dcy) < 85.0:
                        hostile_near = True
                        break

            if dist_player < 85.0 or hostile_near:
                if door.is_locked:
                    if door.lock_reason == "keycard" and player.has_keycard:
                        door.is_locked = False
                        self.world.trigger_alert("🔓 BLAST DOOR UNLOCKED VIA KEYCARD", (1.0, 0.84, 0.0, 1.0))
                        self._trigger_haptic("heavy")
                    else:
                        if int(self.world.wave_time * 2) % 6 == 0:
                            self.world.trigger_alert("🔒 BLAST DOOR LOCKED: REQUIRES KEYCARD", (0.91, 0.30, 0.24, 1.0))

                if not door.is_locked:
                    door.open_progress = min(1.0, door.open_progress + dt * 4.0)
                    door.is_open = (door.open_progress > 0.75)
            else:
                if not door.is_locked and dist_player > 130.0 and not hostile_near:
                    door.open_progress = max(0.0, door.open_progress - dt * 2.5)
                    door.is_open = (door.open_progress > 0.75)

    # --- Terminals Logic ---

    def _update_terminals(self, dt: float):
        player = self.world.player

        # Active gas vent effect
        if self.world.gas_vent_active > 0:
            self.world.gas_vent_active -= dt
            for enemy in self.world.enemies:
                enemy.hp -= 16.0 * dt
                if random.random() < 0.2:
                    self._spawn_sparks(enemy.x, enemy.y, count=2, color=(0.2, 0.95, 0.4, 0.7))

        # Active defense turret effect
        if self.world.turret_active > 0:
            self.world.turret_active -= dt
            self.world.turret_shot_timer += dt
            if self.world.turret_shot_timer >= 0.22:
                self.world.turret_shot_timer = 0.0
                tx, ty = 0.0, -320.0
                target = self._get_nearest_enemy_to_point(tx, ty, max_range=440.0, require_los=True)
                if target:
                    dx = target.x - tx
                    dy = target.y - ty
                    angle = math.atan2(dy, dx)
                    spd = 440.0
                    self.world.projectiles.append(Projectile(
                        x=tx, y=ty,
                        vx=math.cos(angle) * spd,
                        vy=math.sin(angle) * spd,
                        damage=28.0,
                        radius=5.0,
                        penetration=2,
                        color=(0.02, 0.9, 1.0, 1.0)
                    ))

        # Hack proximity
        for term in self.world.map.terminals:
            if term.timer > 0:
                term.timer -= dt

            dist = math.hypot(player.x - term.x, player.y - term.y)
            hack_range = term.radius + player.radius + dp(18)

            if dist <= hack_range:
                if term.terminal_type == "elevator_console":
                    bosses = [e for e in self.world.enemies if e.is_boss]
                    if bosses:
                        if int(self.world.wave_time * 2) % 6 == 0:
                            self.world.trigger_alert("⚠️ PURGE REAPER MECH BOSS TO AUTHORIZE ELEVATOR TRANSIT!", (0.91, 0.30, 0.24, 1.0))
                    else:
                        term.hack_progress += dt / 1.3
                        if term.hack_progress >= 1.0:
                            term.hack_progress = 0.0
                            self.world.floor_completed = True
                            self.world.is_paused = True
                            self.world.trigger_alert("🎉 DECK SECURED! FLOOR COMPLETE!", (0.2, 0.95, 0.65, 1.0))
                            self._trigger_haptic("heavy")
                            if self.on_floor_complete:
                                self.on_floor_complete()
                else:
                    if term.timer <= 0:
                        term.hack_progress += dt / 1.2
                        if term.hack_progress >= 1.0:
                            term.hack_progress = 0.0
                            term.timer = term.cooldown
                            self._trigger_haptic("medium")

                            if term.terminal_type == "gas_vent":
                                self.world.gas_vent_active = 10.0
                                self.world.trigger_alert("☣️ NEURO-GAS VENTS ACTIVATED!", (0.2, 0.95, 0.4, 1.0))
                            elif term.terminal_type == "defense_turret":
                                self.world.turret_active = 12.0
                                self.world.trigger_alert("🛡️ STATION DEFENSE TURRET ONLINE!", (0.02, 0.71, 0.83, 1.0))
                            elif term.terminal_type == "emp_beacon":
                                self.world.trigger_alert("💥 OVERLOAD EMP DISCHARGE!", (0.02, 0.9, 1.0, 1.0))
                                self.emp_visuals.append({
                                    "x": term.x, "y": term.y, "radius": 10.0, "max_radius": 340.0, "alpha": 1.0, "is_cataclysm": False
                                })
                                for enemy in list(self.world.enemies):
                                    if math.hypot(enemy.x - term.x, enemy.y - term.y) <= 340.0:
                                        if self._has_line_of_sight(term.x, term.y, enemy.x, enemy.y):
                                            enemy.hp -= 70.0
            else:
                term.hack_progress = max(0.0, term.hack_progress - dt * 2.0)

    def _update_npcs_proximity(self):
        player = self.world.player
        active = None
        for npc in self.world.map.npcs:
            if math.hypot(player.x - npc.x, player.y - npc.y) <= player.radius + npc.radius + dp(28):
                active = npc
                break
        self.world.active_npc = active

    # --- Weapons & Evolutions Firing Systems (With Line of Sight) ---

    def _update_weapons(self, dt: float):
        player = self.world.player

        # Diamond Hailstorm (Evolution) - Ricochets off walls!
        if "evo_diamond_hailstorm" in player.inventory:
            player.weapon_timers["evo_diamond_hailstorm"] += dt
            cooldown = max(0.40, 0.55 * player.cooldown_mult)
            if player.weapon_timers["evo_diamond_hailstorm"] >= cooldown:
                player.weapon_timers["evo_diamond_hailstorm"] = 0.0
                spd = 400.0
                dmg = 34.0
                for i in range(8):
                    ang = math.radians(i * 45.0 + random.uniform(-6, 6))
                    self.world.projectiles.append(Projectile(
                        x=player.x, y=player.y,
                        vx=math.cos(ang) * spd,
                        vy=math.sin(ang) * spd,
                        damage=dmg, radius=5.0, penetration=3,
                        color=(0.3, 0.95, 1.0, 1.0), is_ricochet=True
                    ))
        elif "shard_pistol" in player.inventory:
            lvl = player.inventory["shard_pistol"]
            cooldown = max(0.18, (0.45 - lvl * 0.05) * player.cooldown_mult)
            player.weapon_timers["shard_pistol"] += dt
            if player.weapon_timers["shard_pistol"] >= cooldown:
                # Requires Line of Sight to target
                target = self._get_nearest_enemy(max_range=320.0, require_los=True)
                if target:
                    player.weapon_timers["shard_pistol"] = 0.0
                    dx = target.x - player.x
                    dy = target.y - player.y
                    angle = math.atan2(dy, dx)
                    spd = 360.0
                    dmg = 12.0 + lvl * 4.0
                    self.world.projectiles.append(Projectile(
                        x=player.x, y=player.y,
                        vx=math.cos(angle) * spd, vy=math.sin(angle) * spd,
                        damage=dmg, penetration=1 if lvl < 3 else 2,
                        color=(0.02, 0.9, 1.0, 1.0)
                    ))
                    if lvl >= 4:
                        spread = 0.16
                        self.world.projectiles.append(Projectile(
                            x=player.x, y=player.y,
                            vx=math.cos(angle + spread) * spd,
                            vy=math.sin(angle + spread) * spd,
                            damage=dmg * 0.85, penetration=1,
                            color=(0.02, 0.9, 1.0, 0.9)
                        ))

        # Apex Swarm Matrix (Evolution)
        if "evo_apex_swarm" in player.inventory:
            player.drone_angle = (player.drone_angle + 220.0 * dt) % 360.0
            player.weapon_timers["evo_apex_swarm"] += dt
            cooldown = max(0.20, 0.28 * player.cooldown_mult)
            for core in self.world.xp_cores:
                if math.hypot(player.x - core.x, player.y - core.y) <= 180.0:
                    dx = player.x - core.x
                    dy = player.y - core.y
                    dist = math.hypot(dx, dy)
                    if dist > 1.0:
                        core.vx += (dx / dist) * 450.0 * dt
                        core.vy += (dy / dist) * 450.0 * dt

            if player.weapon_timers["evo_apex_swarm"] >= cooldown:
                player.weapon_timers["evo_apex_swarm"] = 0.0
                for offset in [0.0, 120.0, 240.0]:
                    rad = math.radians(player.drone_angle + offset)
                    drone_x = player.x + math.cos(rad) * 48.0
                    drone_y = player.y + math.sin(rad) * 48.0
                    target = self._get_nearest_enemy_to_point(drone_x, drone_y, max_range=240.0, require_los=True)
                    if target:
                        dx = target.x - drone_x
                        dy = target.y - drone_y
                        angle = math.atan2(dy, dx)
                        spd = 350.0
                        self.world.projectiles.append(Projectile(
                            x=drone_x, y=drone_y,
                            vx=math.cos(angle) * spd, vy=math.sin(angle) * spd,
                            damage=26.0, radius=5.5, penetration=2,
                            color=(0.2, 0.95, 0.65, 1.0)
                        ))
        elif "seeker_drone" in player.inventory:
            lvl = player.inventory["seeker_drone"]
            player.drone_angle = (player.drone_angle + (140.0 + lvl * 20.0) * dt) % 360.0
            player.weapon_timers["seeker_drone"] += dt
            cooldown = max(0.35, (0.75 - lvl * 0.08) * player.cooldown_mult)
            if player.weapon_timers["seeker_drone"] >= cooldown:
                rad = math.radians(player.drone_angle)
                drone_x = player.x + math.cos(rad) * 44.0
                drone_y = player.y + math.sin(rad) * 44.0
                target = self._get_nearest_enemy_to_point(drone_x, drone_y, max_range=200.0, require_los=True)
                if target:
                    player.weapon_timers["seeker_drone"] = 0.0
                    dx = target.x - drone_x
                    dy = target.y - drone_y
                    angle = math.atan2(dy, dx)
                    spd = 300.0
                    self.world.projectiles.append(Projectile(
                        x=drone_x, y=drone_y,
                        vx=math.cos(angle) * spd, vy=math.sin(angle) * spd,
                        damage=16.0 + lvl * 5.0, radius=5.0, penetration=1,
                        color=(0.2, 0.95, 0.65, 1.0)
                    ))

        # Grey Goo Singularity (Evolution)
        if "evo_grey_goo" in player.inventory:
            aura_radius = 145.0
            player.weapon_timers["evo_grey_goo"] += dt
            if player.weapon_timers["evo_grey_goo"] >= 0.18:
                player.weapon_timers["evo_grey_goo"] = 0.0
                player.hp = min(player.max_hp, player.hp + 1.8)
                for enemy in self.world.enemies:
                    if math.hypot(enemy.x - player.x, enemy.y - player.y) <= aura_radius:
                        if self._has_line_of_sight(player.x, player.y, enemy.x, enemy.y):
                            enemy.hp -= 22.0
                            self._spawn_sparks(enemy.x, enemy.y, count=3, color=(0.1, 0.9, 0.4, 0.8))
        elif "nanite_aura" in player.inventory:
            lvl = player.inventory["nanite_aura"]
            aura_radius = player.radius + 30.0 + lvl * 8.0
            player.weapon_timers["nanite_aura"] += dt
            if player.weapon_timers["nanite_aura"] >= 0.20:
                player.weapon_timers["nanite_aura"] = 0.0
                player.hp = min(player.max_hp, player.hp + 0.35 * lvl)
                for enemy in self.world.enemies:
                    if math.hypot(enemy.x - player.x, enemy.y - player.y) <= aura_radius:
                        if self._has_line_of_sight(player.x, player.y, enemy.x, enemy.y):
                            enemy.hp -= (4.0 + lvl * 2.0)
                            self._spawn_sparks(enemy.x, enemy.y, count=2, color=(0.2, 0.95, 0.65, 0.8))

        # Neuro-Cascade Cataclysm (Evolution)
        if "evo_emp_cataclysm" in player.inventory:
            player.weapon_timers["evo_emp_cataclysm"] += dt
            cooldown = max(2.2, 3.0 * player.cooldown_mult)
            if player.weapon_timers["evo_emp_cataclysm"] >= cooldown:
                player.weapon_timers["evo_emp_cataclysm"] = 0.0
                emp_r = 230.0
                self.emp_visuals.append({
                    "x": player.x, "y": player.y, "radius": 10.0, "max_radius": emp_r, "alpha": 1.0, "is_cataclysm": True
                })
                self._trigger_haptic("medium")
                hit_enemies = []
                for enemy in self.world.enemies:
                    dist = math.hypot(enemy.x - player.x, enemy.y - player.y)
                    if dist <= emp_r:
                        if self._has_line_of_sight(player.x, player.y, enemy.x, enemy.y):
                            enemy.hp -= 65.0
                            enemy.stun_timer = 2.2
                            hit_enemies.append(enemy)
                            if dist > 1.0:
                                enemy.x += ((enemy.x - player.x) / dist) * 60.0
                                enemy.y += ((enemy.y - player.y) / dist) * 60.0
                if len(hit_enemies) >= 2:
                    chain_pts = []
                    for i in range(min(5, len(hit_enemies) - 1)):
                        e1 = hit_enemies[i]
                        e2 = hit_enemies[i+1]
                        chain_pts.extend([e1.x, e1.y, e2.x, e2.y])
                    if chain_pts:
                        self.chain_lightning_visuals.append({"points": chain_pts, "alpha": 1.0})
        elif "emp_shock" in player.inventory:
            lvl = player.inventory["emp_shock"]
            cooldown = max(2.2, (4.2 - lvl * 0.4) * player.cooldown_mult)
            player.weapon_timers["emp_shock"] += dt
            if player.weapon_timers["emp_shock"] >= cooldown:
                player.weapon_timers["emp_shock"] = 0.0
                emp_radius = 140.0 + lvl * 25.0
                dmg = 24.0 + lvl * 10.0
                self.emp_visuals.append({
                    "x": player.x, "y": player.y, "radius": 10.0, "max_radius": emp_radius, "alpha": 1.0, "is_cataclysm": False
                })
                self._trigger_haptic("medium")
                for enemy in self.world.enemies:
                    dist = math.hypot(enemy.x - player.x, enemy.y - player.y)
                    if dist <= emp_radius:
                        if self._has_line_of_sight(player.x, player.y, enemy.x, enemy.y):
                            enemy.hp -= dmg
                            if dist > 1.0:
                                enemy.x += ((enemy.x - player.x) / dist) * 45.0
                                enemy.y += ((enemy.y - player.y) / dist) * 45.0
                            self._spawn_sparks(enemy.x, enemy.y, count=4, color=(0.02, 0.71, 0.83, 1.0))

        # Tachyon Relativistic Lance (Evolution) - Cuts through all matter
        if "evo_tachyon_lance" in player.inventory:
            player.weapon_timers["evo_tachyon_lance"] += dt
            cooldown = max(0.95, 1.15 * player.cooldown_mult)
            if player.weapon_timers["evo_tachyon_lance"] >= cooldown:
                player.weapon_timers["evo_tachyon_lance"] = 0.0
                rad = math.radians(player.facing_angle)
                beam_len = 540.0
                x2 = player.x + math.cos(rad) * beam_len
                y2 = player.y + math.sin(rad) * beam_len
                self.railgun_visuals.append({
                    "x1": player.x, "y1": player.y, "x2": x2, "y2": y2, "alpha": 1.0, "is_tachyon": True
                })
                self._trigger_haptic("heavy")
                dmg = 95.0
                for enemy in self.world.enemies:
                    if self._dist_point_to_segment(enemy.x, enemy.y, player.x, player.y, x2, y2) <= enemy.radius + 18.0:
                        enemy.hp -= dmg
                        self._spawn_sparks(enemy.x, enemy.y, count=8, color=(1.0, 0.3, 0.9, 1.0))
        elif "railgun_beam" in player.inventory:
            lvl = player.inventory["railgun_beam"]
            cooldown = max(1.2, (2.6 - lvl * 0.25) * player.cooldown_mult)
            player.weapon_timers["railgun_beam"] += dt
            if player.weapon_timers["railgun_beam"] >= cooldown:
                player.weapon_timers["railgun_beam"] = 0.0
                rad = math.radians(player.facing_angle)
                beam_max = 380.0
                hit_dist = self._raycast_wall_distance(player.x, player.y, rad, beam_max)
                x2 = player.x + math.cos(rad) * hit_dist
                y2 = player.y + math.sin(rad) * hit_dist
                self.railgun_visuals.append({
                    "x1": player.x, "y1": player.y, "x2": x2, "y2": y2, "alpha": 1.0, "is_tachyon": False
                })
                if hit_dist < beam_max:
                    self._spawn_sparks(x2, y2, count=6, color=(0.85, 0.35, 0.95, 1.0))
                dmg = 35.0 + lvl * 12.0
                for enemy in self.world.enemies:
                    if self._dist_point_to_segment(enemy.x, enemy.y, player.x, player.y, x2, y2) <= enemy.radius + 12.0:
                        if self._has_line_of_sight(player.x, player.y, enemy.x, enemy.y):
                            enemy.hp -= dmg
                            self._spawn_sparks(enemy.x, enemy.y, count=5, color=(0.85, 0.35, 0.95, 1.0))

    def _raycast_wall_distance(self, x1: float, y1: float, angle_rad: float, max_len: float) -> float:
        x2 = x1 + math.cos(angle_rad) * max_len
        y2 = y1 + math.sin(angle_rad) * max_len
        min_t = 1.0

        for wall in self.world.map.walls:
            t, _ = segment_intersects_box(x1, y1, x2, y2, wall.x, wall.y, wall.w, wall.h)
            if t is not None and t < min_t:
                min_t = t

        for door in self.world.map.doors:
            if not door.is_open:
                t, _ = segment_intersects_box(x1, y1, x2, y2, door.x, door.y, door.w, door.h)
                if t is not None and t < min_t:
                    min_t = t

        return min_t * max_len

    def _get_nearest_enemy(self, max_range: float, require_los: bool = True) -> Optional[Enemy]:
        return self._get_nearest_enemy_to_point(self.world.player.x, self.world.player.y, max_range, require_los)

    def _get_nearest_enemy_to_point(self, x: float, y: float, max_range: float, require_los: bool = True) -> Optional[Enemy]:
        nearest = None
        min_dist = max_range
        for enemy in self.world.enemies:
            dist = math.hypot(enemy.x - x, enemy.y - y)
            if dist < min_dist:
                if not require_los or self._has_line_of_sight(x, y, enemy.x, enemy.y):
                    min_dist = dist
                    nearest = enemy
        return nearest

    def _dist_point_to_segment(self, px, py, x1, y1, x2, y2) -> float:
        dx, dy = x2 - x1, y2 - y1
        if dx == 0 and dy == 0:
            return math.hypot(px - x1, py - y1)
        t = max(0.0, min(1.0, ((px - x1) * dx + (py - y1) * dy) / (dx * dx + dy * dy)))
        proj_x = x1 + t * dx
        proj_y = y1 + t * dy
        return math.hypot(px - proj_x, py - proj_y)

    # --- Projectile Updates (Collide with Walls and Closed Doors) ---

    def _update_projectiles(self, dt: float):
        for p in list(self.world.projectiles):
            prev_x = p.x
            prev_y = p.y
            p.x += p.vx * dt
            p.y += p.vy * dt
            p.lifetime -= dt

            if p.lifetime <= 0:
                self.world.projectiles.remove(p)
                continue

            # Continuous collision detection against walls & closed doors
            hit_wall = None
            hit_edge = None
            min_t = None

            for wall in self.world.map.walls:
                t, edge = segment_intersects_box(prev_x, prev_y, p.x, p.y,
                                                 wall.x - p.radius, wall.y - p.radius,
                                                 wall.w + p.radius * 2, wall.h + p.radius * 2)
                if t is not None:
                    if min_t is None or t < min_t:
                        min_t = t
                        hit_edge = edge
                        hit_wall = wall

            if not hit_wall:
                for door in self.world.map.doors:
                    if not door.is_open:
                        t, edge = segment_intersects_box(prev_x, prev_y, p.x, p.y,
                                                         door.x - p.radius, door.y - p.radius,
                                                         door.w + p.radius * 2, door.h + p.radius * 2)
                        if t is not None:
                            if min_t is None or t < min_t:
                                min_t = t
                                hit_edge = edge
                                hit_wall = door

            if hit_wall and min_t is not None:
                impact_x = prev_x + (p.x - prev_x) * min_t
                impact_y = prev_y + (p.y - prev_y) * min_t

                if p.is_ricochet:
                    if hit_edge in ('left', 'right'):
                        p.vx = -p.vx
                    elif hit_edge in ('top', 'bottom'):
                        p.vy = -p.vy
                    else:
                        p.vx = -p.vx
                        p.vy = -p.vy
                    p.x = impact_x + (p.vx / max(1.0, math.hypot(p.vx, p.vy))) * 2.0
                    p.y = impact_y + (p.vy / max(1.0, math.hypot(p.vx, p.vy))) * 2.0
                    p.penetration -= 1
                    self._spawn_sparks(impact_x, impact_y, count=3, color=(0.3, 0.95, 1.0, 1.0))
                    if p.penetration <= 0:
                        self.world.projectiles.remove(p)
                else:
                    self._spawn_sparks(impact_x, impact_y, count=4, color=(0.6, 0.75, 0.95, 0.8))
                    self.world.projectiles.remove(p)
                continue

            # Collision with enemies
            hit = False
            for enemy in self.world.enemies:
                if math.hypot(enemy.x - p.x, enemy.y - p.y) <= enemy.radius + p.radius:
                    enemy.hp -= p.damage
                    p.penetration -= 1
                    self._spawn_sparks(p.x, p.y, count=3, color=p.color)
                    if p.penetration <= 0:
                        hit = True
                        break

            # Collision with crates
            if not hit:
                for crate in self.world.map.crates:
                    if not crate.is_broken:
                        if (crate.x - crate.w/2 <= p.x <= crate.x + crate.w/2 and
                            crate.y - crate.h/2 <= p.y <= crate.y + crate.h/2):
                            crate.hp -= p.damage
                            hit = True
                            self._spawn_sparks(p.x, p.y, count=4, color=(0.95, 0.75, 0.1, 1.0))
                            if crate.hp <= 0:
                                crate.is_broken = True
                                for _ in range(random.randint(2, 4)):
                                    ox = crate.x + random.uniform(-15, 15)
                                    oy = crate.y + random.uniform(-15, 15)
                                    self.world.xp_cores.append(XPCore(ox, oy, value=15))
                            break

            if hit and p in self.world.projectiles:
                self.world.projectiles.remove(p)

    # --- Enemies AI (Doorway Waypoint Navigation & Solid Separation) ---

    def _get_navigation_target_for_enemy(self, enemy: Enemy, goal_x: float, goal_y: float) -> Tuple[float, float]:
        """Intelligently navigates toward goal: direct LOS, local corner rounding, or station waypoint A*."""
        # 1. Direct Line of Sight Check: Move directly
        if self._has_line_of_sight(enemy.x, enemy.y, goal_x, goal_y):
            return (goal_x, goal_y)

        # 2. Local Obstacle Corner Rounding:
        dist_to_goal = math.hypot(goal_x - enemy.x, goal_y - enemy.y)
        if dist_to_goal < 420.0:
            best_corner = None
            min_corner_cost = float('inf')

            for wall in self.world.map.walls:
                if self._line_intersects_rect(enemy.x, enemy.y, goal_x, goal_y, wall.x, wall.y, wall.w, wall.h):
                    margin = enemy.radius + 12.0
                    corners = [
                        (wall.x - margin, wall.y - margin),
                        (wall.x + wall.w + margin, wall.y - margin),
                        (wall.x + wall.w + margin, wall.y + wall.h + margin),
                        (wall.x - margin, wall.y + wall.h + margin)
                    ]
                    for cx, cy in corners:
                        if math.hypot(cx - enemy.x, cy - enemy.y) < 20.0:
                            continue
                        if self._has_line_of_sight(enemy.x, enemy.y, cx, cy):
                            cost = math.hypot(cx - enemy.x, cy - enemy.y) + math.hypot(goal_x - cx, goal_y - cy)
                            if cost < min_corner_cost:
                                min_corner_cost = cost
                                best_corner = (cx, cy)

            if best_corner:
                return best_corner

        # 3. Inter-Room Station Waypoint Graph A* Pathfinding (Deck-specific)
        locked_doors = set()
        for door in self.world.map.doors:
            if door.is_locked:
                locked_doors.add(door.id)

        path = self.world.map.get_path(enemy.x, enemy.y, goal_x, goal_y, locked_doors=locked_doors)
        if path:
            if len(path) <= 1:
                return (goal_x, goal_y)

            # Segment lookahead path follower
            p = (enemy.x, enemy.y)
            best_idx = 1
            min_d = float('inf')
            for i in range(len(path) - 1):
                d = self._dist_point_to_segment(p[0], p[1], path[i][0], path[i][1], path[i+1][0], path[i+1][1])
                if d < min_d:
                    min_d = d
                    if math.hypot(p[0] - path[i+1][0], p[1] - path[i+1][1]) < 35.0 and i + 2 < len(path):
                        best_idx = i + 2
                    else:
                        best_idx = i + 1
            return path[best_idx]

        return (goal_x, goal_y)

    def _update_enemies(self, dt: float):
        player = self.world.player

        for enemy in list(self.world.enemies):
            if not enemy.is_alive():
                self.world.enemies.remove(enemy)
                player.kills += 1

                if enemy.is_captain:
                    self.world.captain_killed = True
                    self.world.keycard_pickup = KeycardPickup(x=enemy.x, y=enemy.y)
                    self.world.trigger_alert("🔑 KEYCARD DROPPED! RETRIEVE IT TO UNLOCK ELEVATOR", (1.0, 0.84, 0.0, 1.0))
                    self._trigger_haptic("heavy")

                if enemy.is_boss:
                    self.world.boss_killed = True
                    self.world.trigger_alert("🏆 REAPER MECH PURGED! ELEVATOR TRANSIT AUTHORIZED!", (0.2, 0.95, 0.65, 1.0))
                    self._trigger_haptic("heavy")

                extra_cores = 2 if "evo_grey_goo" in player.inventory and random.random() < 0.4 else 0
                for _ in range(1 + extra_cores):
                    self.world.xp_cores.append(XPCore(
                        enemy.x + random.uniform(-10, 10),
                        enemy.y + random.uniform(-10, 10),
                        value=enemy.xp_reward
                    ))

                self._spawn_sparks(enemy.x, enemy.y, count=10 if enemy.is_captain or enemy.is_boss else 6, color=enemy.color)
                continue

            if enemy.stun_timer > 0:
                enemy.stun_timer -= dt
                continue

            # --- SENSORY PERCEPTION & AGGRO STATE MACHINE ---
            dist_to_player = math.hypot(player.x - enemy.x, player.y - enemy.y)
            has_los = self._has_line_of_sight(enemy.x, enemy.y, player.x, player.y)

            # Vision Cone calculation (140° forward arc)
            dir_to_player_deg = math.degrees(math.atan2(player.y - enemy.y, player.x - enemy.x))
            diff_ang = abs((dir_to_player_deg - enemy.facing_angle + 180.0) % 360.0 - 180.0)
            in_vision_cone = (diff_ang <= 70.0)

            # Close proximity hearing/awareness (within 130px 360° if line of sight)
            in_close_proximity = (dist_to_player <= 130.0 and has_los)

            # Combat gunshots / weapon discharge detection
            heard_combat_sound = False
            time_since_sound = self.world.wave_time - getattr(self.world, 'last_combat_sound_time', -999.0)
            if time_since_sound < 1.4:
                snd_x, snd_y = getattr(self.world, 'last_combat_sound_pos', (0.0, 0.0))
                if math.hypot(snd_x - enemy.x, snd_y - enemy.y) <= enemy.hearing_range:
                    heard_combat_sound = True

            # Determine if Player is actively Spotted
            is_player_spotted = False
            if enemy.is_boss:
                is_player_spotted = (dist_to_player < 1000.0 or enemy.state == "chase")
            elif enemy.is_captain:
                is_player_spotted = has_los and (dist_to_player <= enemy.aggro_range * 1.3 or in_close_proximity)
            else:
                if has_los and (in_close_proximity or (dist_to_player <= enemy.aggro_range and in_vision_cone)):
                    is_player_spotted = True
                elif enemy.state == "chase" and has_los and dist_to_player <= enemy.aggro_range * 1.5:
                    is_player_spotted = True

            # State Transitions
            if is_player_spotted:
                enemy.last_known_x = player.x
                enemy.last_known_y = player.y
                enemy.facing_angle = dir_to_player_deg

                if enemy.state in ("idle", "patrol"):
                    enemy.state = "alert"
                    enemy.alert_timer = 0.35
                    # Pack Alert Propagation (Alert nearby companions within 240px)
                    for ally in self.world.enemies:
                        if ally is not enemy and ally.state in ("idle", "patrol"):
                            if math.hypot(ally.x - enemy.x, ally.y - enemy.y) <= 240.0:
                                ally.state = "alert"
                                ally.alert_timer = 0.45
                                ally.last_known_x = player.x
                                ally.last_known_y = player.y
                elif enemy.state == "alert":
                    enemy.alert_timer -= dt
                    if enemy.alert_timer <= 0.0:
                        enemy.state = "chase"
                elif enemy.state == "search":
                    enemy.state = "chase"
            else:
                # Player not spotted in current frame
                if heard_combat_sound and enemy.state in ("idle", "patrol"):
                    snd_x, snd_y = getattr(self.world, 'last_combat_sound_pos', (0.0, 0.0))
                    enemy.state = "alert"
                    enemy.alert_timer = 0.4
                    enemy.last_known_x = snd_x
                    enemy.last_known_y = snd_y
                    enemy.facing_angle = math.degrees(math.atan2(snd_y - enemy.y, snd_x - enemy.x))

                if enemy.state == "alert":
                    enemy.alert_timer -= dt
                    if enemy.alert_timer <= 0.0:
                        enemy.state = "search"
                        enemy.search_timer = 4.0
                elif enemy.state == "chase":
                    # Pursuit to last known coordinates
                    dist_to_last_known = math.hypot(enemy.x - enemy.last_known_x, enemy.y - enemy.last_known_y)
                    if dist_to_last_known < 35.0:
                        enemy.state = "search"
                        enemy.search_timer = 3.5
                elif enemy.state == "search":
                    enemy.search_timer -= dt
                    enemy.facing_angle = (enemy.facing_angle + 140.0 * dt) % 360.0
                    if enemy.search_timer <= 0.0:
                        # De-aggro back to idle
                        enemy.state = "idle"
                        enemy.patrol_timer = random.uniform(2.0, 4.5)
                elif enemy.state == "patrol":
                    enemy.patrol_timer -= dt
                    dist_to_patrol = math.hypot(enemy.x - enemy.patrol_target_x, enemy.y - enemy.patrol_target_y)
                    if dist_to_patrol < 25.0 or enemy.patrol_timer <= 0.0:
                        enemy.state = "idle"
                        enemy.patrol_timer = random.uniform(2.0, 5.0)
                elif enemy.state == "idle":
                    enemy.patrol_timer -= dt
                    if enemy.patrol_timer <= 0.0:
                        # Pick a random patrol waypoint within 160 px
                        p_ang = random.uniform(0.0, 6.28)
                        p_dist = random.uniform(50.0, 150.0)
                        enemy.patrol_target_x = enemy.x + math.cos(p_ang) * p_dist
                        enemy.patrol_target_y = enemy.y + math.sin(p_ang) * p_dist
                        enemy.state = "patrol"
                        enemy.patrol_timer = random.uniform(3.0, 5.0)

            # --- Movement Execution Based on State ---
            vx, vy = 0.0, 0.0
            if enemy.state == "chase":
                # If in direct LOS, pursue player directly/flanking; else navigate to last known position
                target_x = player.x if has_los else enemy.last_known_x
                target_y = player.y if has_los else enemy.last_known_y
                tx, ty = self._get_navigation_target_for_enemy(enemy, target_x, target_y)
                dx = tx - enemy.x
                dy = ty - enemy.y
                target_dist = math.hypot(dx, dy)

                if target_dist > 4.0:
                    enemy.facing_angle = math.degrees(math.atan2(dy, dx))
                    if has_los and dist_to_player < 340.0 and not enemy.is_boss:
                        flank_rad = (((hash(enemy.id_name) + int(enemy.max_hp)) % 5) - 2) * 0.16
                        cos_f = math.cos(flank_rad)
                        sin_f = math.sin(flank_rad)
                        ndx = (dx / target_dist)
                        ndy = (dy / target_dist)
                        vx = (ndx * cos_f - ndy * sin_f) * enemy.speed
                        vy = (ndx * sin_f + ndy * cos_f) * enemy.speed
                    else:
                        vx = (dx / target_dist) * enemy.speed
                        vy = (dy / target_dist) * enemy.speed

                    enemy.x += vx * dt
                    enemy.y += vy * dt

                # Enemies in chase push open unlocked sliding doors
                for door in self.world.map.doors:
                    if not door.is_locked and not door.is_open:
                        if math.hypot(enemy.x - (door.x + door.w/2), enemy.y - (door.y + door.h/2)) <= enemy.radius + 30.0:
                            door.open_progress = min(1.0, door.open_progress + dt * 2.8)

            elif enemy.state == "patrol":
                tx, ty = self._get_navigation_target_for_enemy(enemy, enemy.patrol_target_x, enemy.patrol_target_y)
                dx = tx - enemy.x
                dy = ty - enemy.y
                target_dist = math.hypot(dx, dy)
                if target_dist > 6.0:
                    enemy.facing_angle = math.degrees(math.atan2(dy, dx))
                    spd = enemy.speed * 0.40
                    vx = (dx / target_dist) * spd
                    vy = (dy / target_dist) * spd
                    enemy.x += vx * dt
                    enemy.y += vy * dt

            # Wall & Closed Door Collisions for this enemy
            for wall in self.world.map.walls:
                self._resolve_circle_wall_collision(enemy, wall)

            for door in self.world.map.doors:
                if not door.is_open:
                    self._resolve_circle_rect_collision(enemy, door.x, door.y, door.w, door.h)

            # Attack Player on Contact
            if dist_to_player <= player.radius + enemy.radius:
                dmg = max(1.0, enemy.damage - player.armor)
                player.hp -= dmg * dt * 2.0
                self._trigger_haptic("light")

                if player.hp <= 0.0:
                    if getattr(player, "has_stack_insurance", False):
                        player.has_stack_insurance = False
                        player.hp = player.max_hp * 0.50
                        self.world.trigger_alert("🧬 EMERGENCY CORTICAL STACK RESTORE! CHASSIS REBOOTED", (0.2, 0.95, 0.65, 1.0))
                        self._spawn_sparks(player.x, player.y, count=25, color=(0.2, 0.95, 0.65, 1.0))
                        self._trigger_haptic("heavy")
                    else:
                        player.hp = 0.0
                        self.world.is_game_over = True
                        self.on_game_over()
                        return
        # Solid Mass-Weighted Enemy-Enemy Separation (Cannot occupy the same space!)
        enemies = self.world.enemies
        n_enemies = len(enemies)

        def get_mass(e: Enemy) -> float:
            if e.is_boss: return 25.0
            if e.is_captain: return 6.0
            if e.id_name == "exsurgent_husk": return 3.0
            return 1.0

        for _ in range(2):
            for i in range(n_enemies):
                e1 = enemies[i]
                m1 = get_mass(e1)
                for j in range(i + 1, n_enemies):
                    e2 = enemies[j]
                    dx = e2.x - e1.x
                    dy = e2.y - e1.y
                    dist = math.hypot(dx, dy)
                    min_dist = e1.radius + e2.radius + dp(2)

                    if dist < min_dist:
                        if dist <= 0.001:
                            ang = random.uniform(0.0, 6.28)
                            nx, ny = math.cos(ang), math.sin(ang)
                            overlap = min_dist
                        else:
                            nx = dx / dist
                            ny = dy / dist
                            overlap = min_dist - dist

                        m2 = get_mass(e2)
                        total_m = m1 + m2
                        w1 = m2 / total_m
                        w2 = m1 / total_m

                        e1.x -= nx * overlap * w1
                        e1.y -= ny * overlap * w1
                        e2.x += nx * overlap * w2
                        e2.y += ny * overlap * w2

        # Post-separation wall boundary pass to prevent being shoved into walls
        for enemy in enemies:
            for wall in self.world.map.walls:
                self._resolve_circle_wall_collision(enemy, wall)
            for door in self.world.map.doors:
                if not door.is_open:
                    self._resolve_circle_rect_collision(enemy, door.x, door.y, door.w, door.h)

    # --- XP Cores & Keycards Collection ---

    def _update_xp_cores(self, dt: float):
        player = self.world.player

        for core in list(self.world.xp_cores):
            dx = player.x - core.x
            dy = player.y - core.y
            dist = math.hypot(dx, dy)

            if dist <= player.pickup_radius:
                suction_spd = 360.0
                core.vx = (dx / dist) * suction_spd
                core.vy = (dy / dist) * suction_spd
                core.x += core.vx * dt
                core.y += core.vy * dt

                if dist <= player.radius + core.radius:
                    self.world.xp_cores.remove(core)
                    player.xp += core.value

                    if player.xp >= player.xp_to_next:
                        player.xp -= player.xp_to_next
                        player.level += 1
                        player.xp_to_next = int(player.xp_to_next * 1.32 + 15)
                        self.world.is_paused = True
                        self._trigger_haptic("medium")
                        self.on_level_up(player)
                        return

    def _update_keycard_pickup(self):
        player = self.world.player
        kp = self.world.keycard_pickup
        if kp and not kp.collected:
            if math.hypot(player.x - kp.x, player.y - kp.y) <= player.radius + kp.radius:
                kp.collected = True
                player.has_keycard = True
                self.world.trigger_alert("🔓 CLASS-5 KEYCARD ACQUIRED! PROCEED TO TRANSIT ELEVATOR", (1.0, 0.84, 0.0, 1.0))
                self._trigger_haptic("heavy")

    # --- Visual Effects & Alerts ---

    def _update_visual_effects(self, dt: float):
        for emp in list(self.emp_visuals):
            emp["radius"] += (emp["max_radius"] - emp["radius"]) * 14.0 * dt
            emp["alpha"] -= 2.2 * dt
            if emp["alpha"] <= 0.0:
                self.emp_visuals.remove(emp)

        for rb in list(self.railgun_visuals):
            rate = 2.5 if rb.get("is_tachyon") else 3.5
            rb["alpha"] -= rate * dt
            if rb["alpha"] <= 0.0:
                self.railgun_visuals.remove(rb)

        for cl in list(self.chain_lightning_visuals):
            cl["alpha"] -= 3.0 * dt
            if cl["alpha"] <= 0.0:
                self.chain_lightning_visuals.remove(cl)

        for s in list(self.sparks):
            s["x"] += s["vx"] * dt
            s["y"] += s["vy"] * dt
            s["life"] -= dt
            if s["life"] <= 0.0:
                self.sparks.remove(s)

        for a in list(self.world.alert_notifications):
            a["timer"] -= dt
            if a["timer"] <= 0.0:
                self.world.alert_notifications.remove(a)

    def _spawn_sparks(self, x: float, y: float, count: int = 4, color=(1, 1, 1, 1)):
        for _ in range(count):
            ang = random.uniform(0, math.pi * 2)
            spd = random.uniform(40.0, 140.0)
            self.sparks.append({
                "x": x, "y": y,
                "vx": math.cos(ang) * spd,
                "vy": math.sin(ang) * spd,
                "life": random.uniform(0.15, 0.35),
                "color": color
            })

    def _trigger_haptic(self, style: str = "light"):
        if self.host and hasattr(self.host, "hardware") and self.host.hardware:
            try:
                self.host.hardware.vibrate()
            except Exception:
                pass

    # --- Canvas Drawing / Rendering ---

    def redraw(self, *args):
        self.canvas.clear()
        if self.width <= 0 or self.height <= 0:
            return

        cx, cy = self.center_x, self.center_y
        player = self.world.player

        cam_x = cx - player.x
        cam_y = cy - player.y

        with self.canvas:
            # 1. Background Void
            Color(0.03, 0.04, 0.06, 1.0)
            Rectangle(pos=self.pos, size=self.size)

            # 2. Station Rooms Tint & Floors
            for room in self.world.map.rooms:
                rx = cam_x + room.x1
                ry = cam_y + room.y1
                rw = room.x2 - room.x1
                rh = room.y2 - room.y1

                if room.is_cleared:
                    Color(0.04, 0.09, 0.07, 0.6)
                elif room.is_discovered:
                    Color(0.06, 0.08, 0.12, 0.8)
                else:
                    Color(0.03, 0.04, 0.06, 0.9)
                Rectangle(pos=(rx, ry), size=(rw, rh))

                if room.is_cleared:
                    Color(0.2, 0.95, 0.65, 0.25)
                elif room.is_discovered:
                    Color(0.02, 0.71, 0.83, 0.2)
                else:
                    Color(0.15, 0.18, 0.25, 0.1)
                Line(rectangle=(rx, ry, rw, rh), width=1.0)

            # 3. Deck Grid
            Color(0.08, 0.10, 0.15, 0.4)
            grid_spacing = dp(60)
            start_x = int((cam_x - self.world.map.width / 2) % grid_spacing)
            start_y = int((cam_y - self.world.map.height / 2) % grid_spacing)
            for gx in range(int(self.x) + start_x, int(self.x + self.width), int(grid_spacing)):
                Line(points=[gx, self.y, gx, self.y + self.height], width=1.0)
            for gy in range(int(self.y) + start_y, int(self.y + self.height), int(grid_spacing)):
                Line(points=[self.x, gy, self.x + self.width, gy], width=1.0)

            # 4. Station Walls
            Color(0.16, 0.20, 0.30, 1.0)
            for wall in self.world.map.walls:
                wx = cam_x + wall.x
                wy = cam_y + wall.y
                RoundedRectangle(pos=(wx, wy), size=(wall.w, wall.h), radius=[dp(3)])
                Color(0.02, 0.71, 0.83, 0.35)
                Line(rounded_rectangle=(wx, wy, wall.w, wall.h, dp(3)), width=1.0)
                Color(0.16, 0.20, 0.30, 1.0)

            # 5. Sliding Station Doors
            for door in self.world.map.doors:
                dx = cam_x + door.x
                dy = cam_y + door.y

                if door.is_locked:
                    Color(0.91, 0.30, 0.24, 0.95)
                    RoundedRectangle(pos=(dx, dy), size=(door.w, door.h), radius=[dp(3)])
                    Color(1.0, 0.84, 0.0, 1.0)
                    Line(rounded_rectangle=(dx, dy, door.w, door.h, dp(3)), width=1.8)
                elif door.is_open:
                    Color(0.2, 0.95, 0.65, 0.6)
                    Line(rounded_rectangle=(dx, dy, door.w, door.h, dp(2)), width=1.0)
                    Color(0.02, 0.95, 0.65, 0.15)
                    Rectangle(pos=(dx, dy), size=(door.w, door.h))
                else:
                    Color(0.18, 0.24, 0.34, 1.0)
                    RoundedRectangle(pos=(dx, dy), size=(door.w, door.h), radius=[dp(3)])
                    Color(0.02, 0.71, 0.83, 0.85)
                    Line(rounded_rectangle=(dx, dy, door.w, door.h, dp(3)), width=1.4)

            # 6. Supply Crates
            for crate in self.world.map.crates:
                if not crate.is_broken:
                    wx = cam_x + crate.x - crate.w / 2
                    wy = cam_y + crate.y - crate.h / 2
                    Color(0.24, 0.18, 0.08, 1.0)
                    RoundedRectangle(pos=(wx, wy), size=(crate.w, crate.h), radius=[dp(3)])
                    Color(0.95, 0.75, 0.10, 0.9)
                    Line(rounded_rectangle=(wx, wy, crate.w, crate.h, dp(3)), width=1.2)

            # 7. Terminals & Elevator Console
            for term in self.world.map.terminals:
                tx = cam_x + term.x
                ty = cam_y + term.y
                Color(0.10, 0.12, 0.18, 1.0)
                Ellipse(pos=(tx - term.radius, ty - term.radius), size=(term.radius * 2, term.radius * 2))

                if term.terminal_type == "elevator_console":
                    Color(0.2, 0.95, 0.65, 1.0) if not any(e.is_boss for e in self.world.enemies) else Color(1.0, 0.84, 0.0, 1.0)
                elif term.timer > 0:
                    Color(0.5, 0.5, 0.5, 0.6)
                else:
                    Color(0.02, 0.9, 1.0, 1.0)
                Line(circle=(tx, ty, term.radius), width=2.2)

                if term.hack_progress > 0:
                    Color(0.2, 0.95, 0.65, 1.0)
                    sweep = term.hack_progress * 360.0
                    Line(circle=(tx, ty, term.radius + dp(4), 0, sweep), width=3.0)

            # 7b. Station NPCs (Dr. Sorenson, Zephyr, Clinic AGI) - High-Visibility Beacons & Holograms
            for npc in self.world.map.npcs:
                nx = cam_x + npc.x
                ny = cam_y + npc.y

                is_active = (self.world.active_npc == npc)
                pulse = 1.0 + 0.14 * math.sin(self.world.wave_time * 4.0)

                # Vertical Translucent Light Pillar Beacon reaching up to ceiling
                Color(npc.color[0], npc.color[1], npc.color[2], 0.16 + 0.08 * math.sin(self.world.wave_time * 5.0))
                Rectangle(pos=(nx - dp(6), ny), size=(dp(12), dp(110)))
                Color(npc.color[0], npc.color[1], npc.color[2], 0.40)
                Line(points=[nx, ny, nx, ny + dp(110)], width=1.8)

                # Outer Pulsing Aura
                if is_active:
                    Color(1.0, 0.84, 0.0, 0.42)
                else:
                    Color(npc.color[0], npc.color[1], npc.color[2], 0.24)
                Ellipse(pos=(nx - npc.radius * 1.6 * pulse, ny - npc.radius * 1.6 * pulse),
                        size=(npc.radius * 3.2 * pulse, npc.radius * 3.2 * pulse))

                # Platform Pad
                Color(npc.color[0], npc.color[1], npc.color[2], 0.88)
                Ellipse(pos=(nx - npc.radius, ny - npc.radius),
                        size=(npc.radius * 2.0, npc.radius * 2.0))

                # Inner Tech Core
                Color(0.08, 0.10, 0.16, 1.0)
                Ellipse(pos=(nx - npc.radius * 0.65, ny - npc.radius * 0.65),
                        size=(npc.radius * 1.3, npc.radius * 1.3))

                Color(1.0, 0.84, 0.0, 1.0) if is_active else Color(npc.color[0], npc.color[1], npc.color[2], 1.0)
                Line(circle=(nx, ny, npc.radius), width=2.4 if is_active else 1.5)

                # Floating NPC Holographic Banner Badge
                banner_y = ny + dp(85) + math.sin(self.world.wave_time * 3.5) * dp(3)
                badge_w = dp(110)
                badge_h = dp(20)
                Color(0.06, 0.08, 0.14, 0.94)
                RoundedRectangle(pos=(nx - badge_w/2, banner_y - badge_h/2), size=(badge_w, badge_h), radius=[dp(5)])
                Color(npc.color[0], npc.color[1], npc.color[2], 0.95)
                Line(rounded_rectangle=(nx - badge_w/2, banner_y - badge_h/2, badge_w, badge_h, dp(5)), width=1.4)

                if is_active:
                    # Floating Holographic Interaction Badge [E]
                    tag_y = ny + npc.radius + dp(16) + math.sin(self.world.wave_time * 6.0) * dp(3)
                    Color(0.08, 0.10, 0.16, 0.95)
                    RoundedRectangle(pos=(nx - dp(32), tag_y - dp(9)), size=(dp(64), dp(18)), radius=[dp(4)])
                    Color(1.0, 0.84, 0.0, 1.0)
                    Line(rounded_rectangle=(nx - dp(32), tag_y - dp(9), dp(64), dp(18), dp(4)), width=1.8)
                    Line(circle=(nx, tag_y, dp(3.5)), width=2.0)
            # 8. Golden Keycard Pickup
            kp = self.world.keycard_pickup
            if kp and not kp.collected:
                kx = cam_x + kp.x
                ky = cam_y + kp.y
                Color(1.0, 0.84, 0.0, 1.0)
                RoundedRectangle(pos=(kx - dp(10), ky - dp(6)), size=(dp(20), dp(12)), radius=[dp(2)])
                Color(1.0, 1.0, 1.0, 0.9)
                Line(circle=(kx, ky, dp(14)), width=1.5)

            # 9. XP Nanocores
            for core in self.world.xp_cores:
                gx = cam_x + core.x
                gy = cam_y + core.y
                Color(*core.color)
                Ellipse(pos=(gx - core.radius, gy - core.radius), size=(core.radius * 2, core.radius * 2))

            # 10. Enemies & Bosses (With Awareness State Badges & Stealth Cones)
            for enemy in self.world.enemies:
                ex = cam_x + enemy.x
                ey = cam_y + enemy.y
                Color(*enemy.color)
                Ellipse(pos=(ex - enemy.radius, ey - enemy.radius), size=(enemy.radius * 2, enemy.radius * 2))

                if enemy.is_captain:
                    Color(1.0, 0.84, 0.0, 0.85)
                    Line(circle=(ex, ey, enemy.radius + dp(4)), width=2.0)
                elif enemy.is_boss:
                    Color(0.91, 0.30, 0.24, 0.85)
                    Line(circle=(ex, ey, enemy.radius + dp(6)), width=2.5)

                # Health Bar
                if enemy.hp < enemy.max_hp:
                    bar_w = enemy.radius * 2.2
                    bar_h = dp(3)
                    pct = max(0.0, enemy.hp / enemy.max_hp)
                    Color(0.2, 0.2, 0.2, 0.8)
                    Rectangle(pos=(ex - bar_w/2, ey + enemy.radius + dp(3)), size=(bar_w, bar_h))
                    Color(0.91, 0.30, 0.24, 1.0)
                    Rectangle(pos=(ex - bar_w/2, ey + enemy.radius + dp(3)), size=(bar_w * pct, bar_h))

                # Awareness State Indicator (! in red/amber, ? in yellow)
                if enemy.state in ("alert", "chase"):
                    mark_y = ey + enemy.radius + dp(12)
                    col = (0.95, 0.25, 0.2, 1.0) if enemy.state == "chase" else (1.0, 0.80, 0.1, 1.0)
                    Color(*col)
                    Line(points=[ex, mark_y, ex, mark_y + dp(7)], width=2.4)
                    Ellipse(pos=(ex - dp(1.5), mark_y - dp(4)), size=(dp(3), dp(3)))
                elif enemy.state == "search":
                    mark_y = ey + enemy.radius + dp(12)
                    Color(1.0, 0.85, 0.2, 0.95)
                    Line(points=[ex - dp(3), mark_y + dp(6), ex + dp(3), mark_y + dp(6), ex + dp(3), mark_y + dp(3), ex, mark_y + dp(1)], width=1.6)
                    Ellipse(pos=(ex - dp(1.5), mark_y - dp(3)), size=(dp(3), dp(3)))
                elif enemy.state in ("idle", "patrol") and not enemy.is_boss:
                    # Subtle stealth vision cone for tactical sneaking
                    e_rad = math.radians(enemy.facing_angle)
                    cone_len = dp(55)
                    c1x = ex + math.cos(e_rad - 0.6) * cone_len
                    c1y = ey + math.sin(e_rad - 0.6) * cone_len
                    c2x = ex + math.cos(e_rad + 0.6) * cone_len
                    c2y = ey + math.sin(e_rad + 0.6) * cone_len
                    Color(0.9, 0.2, 0.2, 0.05)
                    Line(points=[ex, ey, c1x, c1y, c2x, c2y, ex, ey], width=1.0)
            # 11. Projectiles
            for p in self.world.projectiles:
                px = cam_x + p.x
                py = cam_y + p.y
                Color(*p.color)
                Ellipse(pos=(px - p.radius, py - p.radius), size=(p.radius * 2, p.radius * 2))

            # 12. Visual Effects: EMP Rings
            for emp in self.emp_visuals:
                ex = cam_x + emp["x"]
                ey = cam_y + emp["y"]
                r = emp["radius"]
                if emp.get("is_cataclysm"):
                    Color(1.0, 0.84, 0.0, emp["alpha"] * 0.9)
                    Line(circle=(ex, ey, r), width=3.5)
                    Color(0.02, 0.9, 1.0, emp["alpha"] * 0.7)
                    Line(circle=(ex, ey, r * 0.75), width=2.0)
                else:
                    Color(0.02, 0.71, 0.83, emp["alpha"] * 0.7)
                    Line(circle=(ex, ey, r), width=2.5)

            # 13. Visual Effects: Railgun & Tachyon Beams
            for rb in self.railgun_visuals:
                if rb.get("is_tachyon"):
                    Color(1.0, 0.3, 0.9, rb["alpha"] * 0.95)
                    Line(points=[cam_x + rb["x1"], cam_y + rb["y1"], cam_x + rb["x2"], cam_y + rb["y2"]], width=6.5)
                    Color(1.0, 1.0, 1.0, rb["alpha"])
                    Line(points=[cam_x + rb["x1"], cam_y + rb["y1"], cam_x + rb["x2"], cam_y + rb["y2"]], width=2.0)
                else:
                    Color(0.85, 0.35, 0.95, rb["alpha"] * 0.9)
                    Line(points=[cam_x + rb["x1"], cam_y + rb["y1"], cam_x + rb["x2"], cam_y + rb["y2"]], width=3.5)

            # 14. Visual Effects: Chain Lightning
            for cl in self.chain_lightning_visuals:
                pts = cl["points"]
                cam_pts = []
                for i in range(0, len(pts), 2):
                    cam_pts.extend([cam_x + pts[i], cam_y + pts[i+1]])
                Color(0.02, 0.95, 1.0, cl["alpha"])
                Line(points=cam_pts, width=2.0)

            # 15. Sparks
            for s in self.sparks:
                Color(*s["color"])
                Ellipse(pos=(cam_x + s["x"] - dp(1.5), cam_y + s["y"] - dp(1.5)), size=(dp(3), dp(3)))

            # 16. Player Sleeve (Center of Screen)
            rad = math.radians(player.facing_angle)
            cone_dist = dp(90)
            spread_ang = 0.4
            p1x = cx + math.cos(rad - spread_ang) * cone_dist
            p1y = cy + math.sin(rad - spread_ang) * cone_dist
            p2x = cx + math.cos(rad + spread_ang) * cone_dist
            p2y = cy + math.sin(rad + spread_ang) * cone_dist
            Color(0.02, 0.71, 0.83, 0.12)
            Line(points=[cx, cy, p1x, p1y, p2x, p2y, cx, cy], width=1.0)

            # Grey Goo Singularity Aura
            if "evo_grey_goo" in player.inventory:
                Color(0.1, 0.9, 0.4, 0.35)
                Line(circle=(cx, cy, 145.0), width=3.0)
                Color(0.05, 0.5, 0.2, 0.15)
                Ellipse(pos=(cx - 145.0, cy - 145.0), size=(290.0, 290.0))
            elif "nanite_aura" in player.inventory:
                aura_r = player.radius + 30.0 + player.inventory["nanite_aura"] * 8.0
                Color(0.2, 0.95, 0.65, 0.22)
                Line(circle=(cx, cy, aura_r), width=1.5)

            # Player Body
            morph_colors = {
                "synth": (0.95, 0.45, 0.15, 1.0),
                "fury": (0.75, 0.25, 0.90, 1.0),
                "menton": (0.02, 0.71, 0.83, 1.0),
                "ghost": (0.2, 0.95, 0.65, 1.0)
            }
            body_col = morph_colors.get(player.morph_id, (0.02, 0.71, 0.83, 1.0))
            Color(*body_col)
            Ellipse(pos=(cx - player.radius, cy - player.radius), size=(player.radius * 2, player.radius * 2))

            # Directional Visor Eye
            Color(1.0, 1.0, 1.0, 1.0)
            vx = cx + math.cos(rad) * (player.radius - dp(3))
            vy = cy + math.sin(rad) * (player.radius - dp(3))
            Ellipse(pos=(vx - dp(3), vy - dp(3)), size=(dp(6), dp(6)))

            # Orbital Drones
            if "evo_apex_swarm" in player.inventory:
                for off in [0.0, 120.0, 240.0]:
                    d_rad = math.radians(player.drone_angle + off)
                    dx_d = cx + math.cos(d_rad) * dp(44)
                    dy_d = cy + math.sin(d_rad) * dp(44)
                    Color(1.0, 0.84, 0.0, 1.0)
                    Ellipse(pos=(dx_d - dp(5), dy_d - dp(5)), size=(dp(10), dp(10)))
                Color(1.0, 0.84, 0.0, 0.4)
                Line(circle=(cx, cy, dp(44)), width=1.2)
            elif "seeker_drone" in player.inventory:
                d_rad = math.radians(player.drone_angle)
                d_dist = dp(38)
                drone_cx = cx + math.cos(d_rad) * d_dist
                drone_cy = cy + math.sin(d_rad) * d_dist
                Color(0.2, 0.95, 0.65, 1.0)
                Ellipse(pos=(drone_cx - dp(5), drone_cy - dp(5)), size=(dp(10), dp(10)))
                Color(0.02, 0.71, 0.83, 0.4)
                Line(circle=(cx, cy, d_dist), width=1.0)

            # 17. Virtual Joystick Visualizer
            if self.touch_stick_origin and self.touch_stick_current:
                ox, oy = self.touch_stick_origin
                cx_t, cy_t = self.touch_stick_current
                Color(0.2, 0.25, 0.35, 0.4)
                Ellipse(pos=(ox - dp(45), oy - dp(45)), size=(dp(90), dp(90)))
                Color(0.02, 0.71, 0.83, 0.8)
                Ellipse(pos=(cx_t - dp(18), cy_t - dp(18)), size=(dp(36), dp(36)))
