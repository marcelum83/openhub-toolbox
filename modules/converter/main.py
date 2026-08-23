"""
OpenHub Module: Universal Unit Converter
Physical, scientific, and astronomical/lunar gravity conversion matrices.
"""
from kivy.uix.boxlayout import BoxLayout
from kivy.uix.gridlayout import GridLayout
from kivy.uix.label import Label
from kivy.uix.button import Button
from kivy.uix.textinput import TextInput
from kivy.uix.scrollview import ScrollView

CONVERSIONS = {
    "Length": {
        "Base": "Meter",
        "Units": {
            "Millimeter (mm)": 0.001,
            "Centimeter (cm)": 0.01,
            "Meter (m)": 1.0,
            "Kilometer (km)": 1000.0,
            "Inch (in)": 0.0254,
            "Foot (ft)": 0.3048,
            "Yard (yd)": 0.9144,
            "Mile (mi)": 1609.344,
            "Nautical Mile": 1852.0
        }
    },
    "Mass & Lunar": {
        "Base": "Kilogram",
        "Units": {
            "Gram (g)": 0.001,
            "Kilogram (kg)": 1.0,
            "Ounce (oz)": 0.0283495,
            "Pound (lb)": 0.453592,
            "Metric Ton (t)": 1000.0,
            "Earth Weight (N)": 9.80665,
            "Lunar Weight (N)": 1.622,
            "Mars Weight (N)": 3.721
        }
    },
    "Volume": {
        "Base": "Liter",
        "Units": {
            "Milliliter (ml)": 0.001,
            "Liter (L)": 1.0,
            "Cubic Meter (m³)": 1000.0,
            "US Fluid Oz (fl oz)": 0.0295735,
            "US Gallon (gal)": 3.78541,
            "Imperial Gallon": 4.54609,
            "Cup (US)": 0.236588
        }
    },
    "Pressure": {
        "Base": "Pascal",
        "Units": {
            "Pascal (Pa)": 1.0,
            "Kilopascal (kPa)": 1000.0,
            "Bar": 100000.0,
            "PSI (lbf/in²)": 6894.76,
            "Atmosphere (atm)": 101325.0,
            "Torr / mmHg": 133.322
        }
    },
    "Temperature": {
        "Base": "Special",
        "Units": ["Celsius (°C)", "Fahrenheit (°F)", "Kelvin (K)"]
    }
}

from kivy.metrics import dp, sp

class OpenHubModule(BoxLayout):
    def __init__(self, **kwargs):
        super().__init__(orientation='vertical', padding=dp(16), spacing=dp(12), **kwargs)
        self.host = None
        self.current_category = "Length"
        
        # 1. Category Switcher Bar
        cat_scroll = ScrollView(size_hint_y=None, height=dp(52), do_scroll_x=True, do_scroll_y=False)
        self.cat_box = BoxLayout(orientation='horizontal', size_hint_x=None, spacing=dp(8))
        self.cat_box.bind(minimum_width=self.cat_box.setter('width'))
        
        self.cat_btns = {}
        for cat in CONVERSIONS.keys():
            b = Button(
                text=cat,
                size_hint_x=None,
                width=dp(130),
                background_normal="",
                background_color=(0.02, 0.71, 0.83, 1) if cat == self.current_category else (0.13, 0.13, 0.19, 1),
                color=(0.05, 0.05, 0.08, 1) if cat == self.current_category else (0.95, 0.95, 0.97, 1),
                bold=True,
                font_size="15sp"
            )
            b.bind(on_release=lambda inst, c=cat: self.select_category(c))
            self.cat_btns[cat] = b
            self.cat_box.add_widget(b)
        cat_scroll.add_widget(self.cat_box)
        self.add_widget(cat_scroll)

        # 2. Input Number Box
        input_row = BoxLayout(orientation='horizontal', size_hint_y=None, height=dp(58), spacing=dp(10))
        self.lbl_from = Label(text="Input Value:", font_size="16sp", size_hint_x=0.35, halign='left')
        self.lbl_from.bind(size=self.lbl_from.setter('text_size'))
        input_row.add_widget(self.lbl_from)

        self.num_input = TextInput(
            text="1.0",
            multiline=False,
            font_size="22sp",
            background_color=(0.09, 0.09, 0.13, 1),
            foreground_color=(0.02, 0.71, 0.83, 1),
            cursor_color=(0.02, 0.71, 0.83, 1),
            padding=[dp(12), dp(12), dp(12), dp(12)]
        )
        self.num_input.bind(text=self.recalculate)
        input_row.add_widget(self.num_input)
        self.add_widget(input_row)

        # 3. Source Unit Selector
        unit_sel_row = BoxLayout(orientation='horizontal', size_hint_y=None, height=40, spacing=8)
        unit_sel_row.add_widget(Label(text="From Unit:", size_hint_x=0.35, halign='left'))
        self.btn_src_unit = Button(
            text="Meter (m)",
            background_normal="",
            background_color=(0.13, 0.13, 0.19, 1),
            color=(0.95, 0.95, 0.97, 1),
            bold=True
        )
        self.btn_src_unit.bind(on_release=self.cycle_source_unit)
        unit_sel_row.add_widget(self.btn_src_unit)
        self.add_widget(unit_sel_row)

        # 4. Results List
        self.results_scroll = ScrollView()
        self.results_grid = GridLayout(cols=1, spacing=8, size_hint_y=None, padding=[0, 6, 0, 6])
        self.results_grid.bind(minimum_height=self.results_grid.setter('height'))
        self.results_scroll.add_widget(self.results_grid)
        self.add_widget(self.results_scroll)

        self.select_category("Length")

    def on_load(self, host_api):
        self.host = host_api

    def select_category(self, cat):
        self.current_category = cat
        for c, btn in self.cat_btns.items():
            if c == cat:
                btn.background_color = (0.02, 0.71, 0.83, 1)
                btn.color = (0.05, 0.05, 0.08, 1)
            else:
                btn.background_color = (0.13, 0.13, 0.19, 1)
                btn.color = (0.95, 0.95, 0.97, 1)
        
        # Set default source unit
        if cat == "Temperature":
            self.btn_src_unit.text = "Celsius (°C)"
        else:
            units = list(CONVERSIONS[cat]["Units"].keys())
            self.btn_src_unit.text = units[0]

        self.recalculate()

    def cycle_source_unit(self, instance):
        if self.current_category == "Temperature":
            units = CONVERSIONS["Temperature"]["Units"]
        else:
            units = list(CONVERSIONS[self.current_category]["Units"].keys())

        idx = units.index(self.btn_src_unit.text) if self.btn_src_unit.text in units else 0
        next_idx = (idx + 1) % len(units)
        self.btn_src_unit.text = units[next_idx]
        self.recalculate()

    def recalculate(self, *args):
        self.results_grid.clear_widgets()
        try:
            val = float(self.num_input.text.strip())
        except ValueError:
            return

        cat = self.current_category
        src_unit = self.btn_src_unit.text

        if cat == "Temperature":
            # Temp conversions
            if "Celsius" in src_unit:
                c = val
                f = (c * 9/5) + 32
                k = c + 273.15
            elif "Fahrenheit" in src_unit:
                f = val
                c = (f - 32) * 5/9
                k = c + 273.15
            else: # Kelvin
                k = val
                c = k - 273.15
                f = (c * 9/5) + 32
            
            res = [("Celsius (°C)", c), ("Fahrenheit (°F)", f), ("Kelvin (K)", k)]
            for name, out in res:
                self._add_result_row(name, f"{out:.2f}")
        else:
            unit_map = CONVERSIONS[cat]["Units"]
            if src_unit not in unit_map:
                return
            
            # Convert to base unit
            base_val = val * unit_map[src_unit]
            
            for target_name, target_factor in unit_map.items():
                converted = base_val / target_factor
                if abs(converted) >= 1000000 or (abs(converted) < 0.0001 and converted != 0):
                    formatted = f"{converted:.4e}"
                else:
                    formatted = f"{converted:.4f}".rstrip('0').rstrip('.')
                self._add_result_row(target_name, formatted)

    def _add_result_row(self, unit_name, value_str):
        row = BoxLayout(orientation='horizontal', size_hint_y=None, height=44, padding=[12, 6, 12, 6])
        lbl_name = Label(text=unit_name, size_hint_x=0.55, halign='left', color=(0.8, 0.8, 0.85, 1))
        lbl_name.bind(size=lbl_name.setter('text_size'))
        row.add_widget(lbl_name)
        
        lbl_val = Label(text=value_str, size_hint_x=0.45, halign='right', bold=True, color=(0.02, 0.71, 0.83, 1))
        lbl_val.bind(size=lbl_val.setter('text_size'))
        row.add_widget(lbl_val)
        self.results_grid.add_widget(row)
