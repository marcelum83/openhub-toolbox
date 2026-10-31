# 🧠 Aurelian Hub | Technical Specifications

This document serves as the formal technical reference for the **Intelligence Dashboard** and its visual components.

## 🚀 The Hub Data Engine (JSON-Enabled)
The `HUB_USE` command now supports **JSON values**, allowing for complex, multi-dimensional data structures to be passed into Jinja2 templates.

**Syntax:**
`HUB_USE: component.html | key1={"json": "data"} | key2=simple_string`

---

## 📋 Standard Component: task_list.html
This is the premium, glassmorphism-based task list. Use it to visualize missions and project progress.

### Data Schema (Jinja2)
- `title`: (String) Header for the task list.
- `tasks`: (List of Objects)
    - `description`: (String) The task text.
    - `completed`: (Boolean) True for ✓, False for •.
    - `link`: (String, Optional) A URL to make the task clickable.
    - `meta`: (String, Optional) Small subtext for additional context.
- `footer`: (String, Optional) Bottom status text.

### Source Code Reference
```html
<div style="font-family: 'Segoe UI', Roboto, Helvetica, Arial, sans-serif; background: rgba(20, 27, 36, 0.7); backdrop-filter: blur(10px); color: #e0e7ee; padding: 25px; border-radius: 12px; border: 1px solid rgba(76, 201, 240, 0.3); margin-bottom: 20px; box-shadow: 0 8px 32px rgba(0,0,0,0.4); max-width: 100%;">
    <div style="display: flex; align-items: center; justify-content: space-between; margin-bottom: 20px; border-bottom: 1px solid rgba(76, 201, 240, 0.2); padding-bottom: 12px;">
        <h3 style="color: #4cc9f0; margin: 0; font-size: 1.1rem; letter-spacing: 1px; text-transform: uppercase;">
            <span style="margin-right: 10px;">📋</span>{{ title | default('Mission Tasks') }}
        </h3>
        <span style="font-size: 0.75rem; color: #8899a6; background: rgba(76, 201, 240, 0.1); padding: 4px 10px; border-radius: 20px; border: 1px solid rgba(76, 201, 240, 0.2);">
            {{ tasks | length }} Items
        </span>
    </div>

    <div style="display: flex; flex-direction: column; gap: 12px;">
        {% for task in tasks %}
        <div style="background: rgba(255,255,255,0.03); border: 1px solid rgba(255,255,255,0.05); border-radius: 8px; padding: 12px 16px; display: flex; align-items: flex-start; gap: 14px; transition: transform 0.2s, background 0.2s;">
            <div style="min-width: 24px; height: 24px; display: flex; align-items: center; justify-content: center; border-radius: 50%; background: {{ 'rgba(74, 222, 128, 0.15)' if task.completed else 'rgba(251, 191, 36, 0.1)' }}; border: 1px solid {{ '#4ade80' if task.completed else '#fbbf24' }}; color: {{ '#4ade80' if task.completed else '#fbbf24' }}; font-size: 0.8rem;">
                {% if task.completed %}✓{% else %}•{% endif %}
            </div>
            
            <div style="flex: 1;">
                <div style="color: {{ '#8899a6' if task.completed else '#e0e7ee' }}; font-size: 0.95rem; font-weight: 500; text-decoration: {{ 'line-through' if task.completed else 'none' }}; line-height: 1.4;">
                    {% if task.link %}
                    <a href="{{ task.link }}" style="color: #4cc9f0; text-decoration: none; border-bottom: 1px dashed rgba(76, 201, 240, 0.5);">{{ task.description }}</a>
                    {% else %}
                    {{ task.description }}
                    {% endif %}
                </div>
                {% if task.meta %}
                <div style="font-size: 0.75rem; color: #8899a6; margin-top: 4px; display: flex; align-items: center; gap: 8px;">
                    <span style="display: inline-block; width: 4px; height: 4px; border-radius: 50%; background: #8899a6;"></span>
                    {{ task.meta }}
                </div>
                {% endif %}
            </div>
        </div>
        {% endfor %}
    </div>

    {% if footer %}
    <div style="margin-top: 20px; padding-top: 12px; border-top: 1px solid rgba(255,255,255,0.05); font-size: 0.8rem; color: #8899a6; display: flex; align-items: center; justify-content: space-between;">
        <span>{{ footer }}</span>
        <span style="opacity: 0.5;">Aurelian Intelligence Unit</span>
    </div>
    {% endif %}
</div>
```

---

## 📊 Standard Component: status_grid.html
A high-impact grid view for monitoring system vitals and project metrics.

### Data Schema (Jinja2)
- `title`: (String) Header for the grid.
- `metrics`: (List of Objects)
    - `label`: (String) The name of the metric (e.g., "CPU").
    - `value`: (String/Number) The current value.
    - `unit`: (String, Optional) Unit suffix (e.g., "%", "ms").
    - `status`: (String) One of: `success`, `warning`, `critical`, `normal`.
    - `trend`: (String, Optional) Change indicator (e.g., "+5%").
- `footer`: (String, Optional) Bottom status text.

### Example Usage
`HUB_USE: status_grid.html | title="Agent Vitals" | metrics=[{"label": "Curiosity", "value": "88", "unit": "%", "status": "success"}, {"label": "Latency", "value": "250", "unit": "ms", "status": "warning"}]`

---

## 📖 Standard Component: story_viewer.html
A narrative-focused component for branching stories and interactive choices.

### Data Schema (Jinja2)
- `scene_id`: (String) Unique identifier for the current state/scene (e.g., "intro").
- `scene_text`: (String) The narrative content for the current scene. Supports HTML.
- `choices`: (List of Objects)
    - `label`: (String) The text displayed on the button.
    - `id`: (String, Optional) A unique identifier for this choice. Defaults to label.

### ⛓️ Strategic Narrative Protocol
The Hub uses the **Strategic Narrative Protocol** for bi-directional communication. When a choice is clicked:
1. The component sends a signal to the Hub via `postMessage`.
2. The Hub automatically sends a structured JSON signal to the agent:
   `[CHOICE_MADE: {"scene": "[scene_id]", "id": "[choice_id]", "label": "[choice_label]"}]`
3. This allows the Agent to parse the choice as structured data for complex narrative branching.

---

## 📊 Standard Component: risk_matrix.html
A 5x5 strategic grid for Impact (1-5) vs. Probability (1-5).

### Data Schema (Jinja2)
- `title`: (String) Header for the matrix.
- `risks`: (List of Objects)
    - `label`: (String) Text label for the risk node.
    - `impact`: (Integer, 1-5) Higher is more severe.
    - `prob`: (Integer, 1-5) Higher is more likely.
    - `severity`: (Enum: "critical", "high", "medium", "low") Determines node color.

---

## 🌳 Standard Component: simple_diagram.html
A linear vertical flow of impact nodes.

### Data Schema (Jinja2)
- `title`: (String) Header for the diagram.
- `nodes`: (List of Objects)
    - `label`: (String) Text for the node box.
    - `type`: (Enum: "critical", "warning", "normal") Determines styling.

---

## � Standard Component: md_viewer_editor.html
A dual-mode component for viewing and editing Markdown files.

### Data Schema (Jinja2)
- `title`: (String) Header for the component.
- `markdown_content`: (String, Safe HTML) The rendered markdown content for the "View" mode.
- `markdown_raw`: (String) The raw markdown source for the "Edit" mode.
- `file_path`: (String) Metadata about where the file is located.

### Interactivity
Sends a `[MARKDOWN_UPDATE: ...]` signal when the "Save" button is pressed.

---

## �📊 Auto-Diagramming (Mermaid.js)
The Hub automatically extracts and renders **Mermaid code blocks** from your responses into the Intelligence View. No special tags are required—just use standard triple-backtick markdown fences with `mermaid` language identifier.
