import sys
import json
import uuid
import re
from PySide6.QtWidgets import (
    QApplication, QMainWindow, QWidget, QVBoxLayout, QHBoxLayout, 
    QTextEdit, QLineEdit, QPushButton, QLabel, QFrame, QScrollArea,
    QSizePolicy, QProgressBar, QListWidget, QAbstractItemView, QStackedWidget
)
from PySide6.QtCore import Qt, Signal, QPropertyAnimation, QEasingCurve
from PySide6.QtGui import QFont, QColor

# --- SDK SCHEMA v1.1.1 ---
SDK_SCHEMA = {
    "constraints": {
        "metric_range": (0, 100),
        "max_data_items": 50,
        "max_label_length": 32,
        "id_format": r"node-[a-f0-9]{4}"
    },
    "tokens": {
        "primary": "#3B82F6", "success": "#10B981", "danger": "#EF4444",
        "surface": "#1E293B", "accent": "#F59E0B"
    }
}

class BaseSemanticElement(QFrame):
    def __init__(self, eid, role, title):
        super().__init__()
        self.eid, self.role = eid, role
        clean_title = title[:SDK_SCHEMA["constraints"]["max_label_length"]]
        self.state = {"title": clean_title, "color": "primary"}
        self.capabilities = ["color_change"] 
        self.setMinimumHeight(120)
        self.layout = QVBoxLayout(self)
        self.header = QLabel(clean_title)
        self.header.setStyleSheet("font-weight: bold; color: white; font-size: 13px;")
        self.layout.addWidget(self.header)
        self.meta = QLabel(f"{role.upper()} | {eid}")
        self.meta.setStyleSheet("font-size: 8px; color: rgba(255,255,255,0.4);")
        self.layout.addWidget(self.meta)
        self.apply_base_style()

    def apply_base_style(self):
        bg = SDK_SCHEMA["tokens"].get(self.state["color"], "#3B82F6")
        self.setStyleSheet(f"BaseSemanticElement {{ background-color: {bg}; border-radius: 12px; padding: 10px; margin: 5px; border: 1px solid rgba(255,255,255,0.1); }}")

    def pulse(self):
        anim = QPropertyAnimation(self, b"windowOpacity", self)
        anim.setDuration(200); anim.setStartValue(0.6); anim.setEndValue(1.0); anim.start()

class MetricElement(BaseSemanticElement):
    def __init__(self, eid, role, title):
        super().__init__(eid, role, title)
        self.capabilities.append("numeric_update")
        self.state["value"] = 0
        self.bar = QProgressBar()
        self.bar.setRange(*SDK_SCHEMA["constraints"]["metric_range"])
        self.bar.setStyleSheet("QProgressBar { border-radius: 5px; background: rgba(0,0,0,0.2); text-align: center; color: white; } QProgressBar::chunk { background-color: white; border-radius: 5px; }")
        self.layout.insertWidget(1, self.bar)

    def update_view(self, val):
        min_v, max_v = SDK_SCHEMA["constraints"]["metric_range"]
        clamped_val = max(min_v, min(max_v, int(val)))
        self.state["value"] = clamped_val
        self.bar.setValue(clamped_val)
        self.header.setText(f"{self.state['title']} ({clamped_val}%)")

class DataViewElement(BaseSemanticElement):
    def __init__(self, eid, role, title):
        super().__init__(eid, role, title)
        self.capabilities.append("list_append")
        self.state["items"] = []
        self.list_widget = QListWidget()
        self.list_widget.setStyleSheet("background: transparent; border: none; color: white;")
        self.layout.insertWidget(1, self.list_widget)

    def update_view(self, new_item=None):
        if new_item: self.state["items"].append(new_item)
        limit = SDK_SCHEMA["constraints"]["max_data_items"]
        if len(self.state["items"]) > limit: self.state["items"] = self.state["items"][-limit:]
        self.list_widget.clear()
        self.list_widget.addItems(self.state["items"])
        self.header.setText(f"{self.state['title']} [{len(self.state['items'])} items]")

class StatusElement(BaseSemanticElement):
    def __init__(self, eid, role, title):
        super().__init__(eid, role, title)
        self.capabilities.append("toggle_status")
        self.state["active"] = False
        self.indicator = QLabel("OFFLINE")
        self.indicator.setAlignment(Qt.AlignCenter)
        self.indicator.setStyleSheet("background: rgba(0,0,0,0.3); border-radius: 4px; padding: 5px; font-weight: bold;")
        self.layout.insertWidget(1, self.indicator)

    def update_view(self):
        status = "ONLINE" if self.state["active"] else "OFFLINE"
        color = SDK_SCHEMA["tokens"]["success"] if self.state["active"] else SDK_SCHEMA["tokens"]["danger"]
        self.indicator.setText(status)
        self.indicator.setStyleSheet(f"background: rgba(0,0,0,0.3); border-radius: 4px; padding: 5px; font-weight: bold; color: {color};")

class NeuroShellOS(QMainWindow):
    def __init__(self):
        super().__init__()
        self.setWindowTitle("NeuroShellOS | SDK v1.1.1 Patch")
        self.resize(1100, 800)
        self.setStyleSheet("background-color: #020617; color: #F8FAFC;")
        self.stack = QStackedWidget()
        self.setCentralWidget(self.stack)

        self.workspace = QWidget()
        self.stack.addWidget(self.workspace)
        ws_layout = QHBoxLayout(self.workspace)
        
        self.canvas = QWidget()
        self.canvas_layout = QVBoxLayout(self.canvas)
        self.canvas_layout.addStretch()
        self.scroll = QScrollArea()
        self.scroll.setWidgetResizable(True)
        self.scroll.setWidget(self.canvas)
        ws_layout.addWidget(self.scroll, stretch=2)
        
        panel = QWidget()
        panel.setFixedWidth(400)
        panel_layout = QVBoxLayout(panel)
        
        header_area = QHBoxLayout()
        header_label = QLabel("<b>SEMANTIC INTERPRETER</b>")
        badge = QLabel("v1.1.1")
        badge.setStyleSheet("background: #10B981; color: black; border-radius: 4px; padding: 2px 6px; font-size: 9px; font-weight: bold;")
        header_area.addWidget(header_label)
        header_area.addStretch()
        header_area.addWidget(badge)
        
        self.log_display = QTextEdit(); self.log_display.setReadOnly(True)
        self.input = QLineEdit(); self.input.setPlaceholderText("Command...")
        self.input.returnPressed.connect(self.process_intent)
        
        self.help_btn = QPushButton("Developer Notes")
        self.help_btn.setStyleSheet("background: #1E293B; color: #94A3B8; border: 1px solid #334155; padding: 8px; border-radius: 4px;")
        self.help_btn.clicked.connect(lambda: self.stack.setCurrentIndex(1))

        panel_layout.addLayout(header_area)
        panel_layout.addWidget(self.log_display)
        panel_layout.addWidget(self.input)
        panel_layout.addWidget(self.help_btn)
        ws_layout.addWidget(panel)

        self.about_page = QWidget(); self.stack.addWidget(self.about_page)
        about_layout = QVBoxLayout(self.about_page); about_layout.setContentsMargins(50, 50, 50, 50)
        dev_header = QLabel("v1.1.1 Pre-Alpha"); dev_header.setStyleSheet("font-size: 24px; font-weight: bold; color: #F59E0B;")
        dev_notes = QLabel("<b>PROJECT STATUS:</b> Pre-Alpha / Concept Validation Prototype<br><br>"
            "<b>PROOF OF CONCEPT:</b> This prototype is built to show that a <b>Semantic Metadata Layer</b> can replace traditional hard-coded GUIs. "
            "It proves that interfaces can be dynamic, evolving based on the intent of the operator rather than static layouts.<br><br>"
            "<b>THE HUMAN-AI BRIDGE:</b> Currently, the input is provided by humans to demonstrate functionality. In a real-world application, "
            "<b>the input will be purely AI-driven</b>. An AI agent's raw reasoning will be intercepted and converted into these specific "
            "SDK commands automatically. This environment serves as the visual playground for verifying that the underlying logic works.")
        dev_notes.setWordWrap(True); dev_notes.setStyleSheet("font-size: 14px; line-height: 160%; color: #CBD5E1;")
        back_btn = QPushButton("Return"); back_btn.setFixedWidth(200); back_btn.clicked.connect(lambda: self.stack.setCurrentIndex(0))
        about_layout.addWidget(dev_header); about_layout.addSpacing(20); about_layout.addWidget(dev_notes); about_layout.addStretch(); about_layout.addWidget(back_btn)

        self.registry = {}
        self.sys_log("Kernel Online. Semantic Disambiguator Active.", "#10B981")

    def sys_log(self, msg, color="#94A3B8"):
        self.log_display.append(f"<span style='color:{color};'>System: {msg}</span>")

    def process_intent(self):
        raw_text = self.input.text().strip()
        self.input.clear()
        if not raw_text: return
        self.log_display.append(f"<b>Human:</b> {raw_text}")
        text = raw_text.lower()

        target_id = None
        id_match = re.search(SDK_SCHEMA["constraints"]["id_format"], text)
        if id_match: target_id = id_match.group(0)

        # DISAMBIGUATION LOGIC
        intent = "unknown"
        
        # Detect Interaction Markers
        is_explicit_interact = any(w in text for w in ["toggle", "switch", "set node", "update node"])
        is_append_interact = ("add item" in text or "add to" in text or "log" in text or "append" in text)
        
        if target_id and (is_explicit_interact or is_append_interact or "node-" in text):
            if any(w in text for w in ["toggle", "switch"]): intent = "INTERACT_TOGGLE"
            elif any(w in text for w in ["append", "item", "put", "insert", "log", "add to"]): intent = "INTERACT_APPEND"
            elif any(w in text for w in ["update", "set", "push", "change"]): intent = "INTERACT_NUMERIC"
        
        # Detect Creation Markers (Only if not already flagged as interaction)
        if intent == "unknown" and any(w in text for w in ["add", "new", "create", "make"]):
            if any(w in text for w in ["progress", "bar", "percent"]): intent = "CREATE_METRIC"
            elif any(w in text for w in ["data", "list", "view", "logs"]): intent = "CREATE_DATA"
            elif any(w in text for w in ["status", "indicator", "light", "toggle"]): intent = "CREATE_STATUS"
            else: intent = "CREATE_BASE"

        quoted = re.findall(r"['\"](.*?)['\"]", raw_text)
        label = quoted[0] if quoted else ""
        if not label:
            label_match = re.search(r"(?:called|named|item|for|to)\s+(.*)", raw_text, re.I)
            label = label_match.group(1).strip() if label_match else raw_text.split()[-1].capitalize()
        label = re.sub(SDK_SCHEMA["constraints"]["id_format"], "", label).strip()

        self.execute_intent(intent, target_id, label, text)

    def execute_intent(self, intent, tid, label, raw):
        if tid and tid not in self.registry:
            self.sys_log(f"Error: Node '{tid}' not found.", "#EF4444"); return

        success, msg = False, ""
        if intent.startswith("CREATE_"):
            eid = f"node-{str(uuid.uuid4())[:4]}"
            if intent == "CREATE_METRIC": el = MetricElement(eid, "metric_display", label)
            elif intent == "CREATE_DATA": el = DataViewElement(eid, "data_view", label)
            elif intent == "CREATE_STATUS": el = StatusElement(eid, "status_indicator", label)
            else: el = BaseSemanticElement(eid, "primary_action", label)
            self.canvas_layout.insertWidget(self.canvas_layout.count()-1, el)
            self.registry[eid] = el; msg = f"Created {el.role} ({eid})"; success = True
        elif intent == "INTERACT_NUMERIC":
            target = self.registry[tid]
            if "numeric_update" in target.capabilities:
                val_match = re.search(r"\b(\d+)\b", raw.replace(tid, ""))
                if val_match:
                    target.update_view(int(val_match.group(1)))
                    target.pulse(); msg = f"Set {tid} to {target.state['value']}%"; success = True
            else: msg = f"Capability Error: {tid} is not a metric."
        elif intent == "INTERACT_TOGGLE":
            target = self.registry[tid]
            if "toggle_status" in target.capabilities:
                target.state["active"] = not target.state["active"]
                target.update_view(); target.pulse(); msg = f"Toggled {tid}"; success = True
        elif intent == "INTERACT_APPEND":
            target = self.registry[tid]
            if "list_append" in target.capabilities:
                target.update_view(label); target.pulse(); msg = f"Logged data to {tid}"; success = True
            else: msg = f"Capability Error: {tid} is not a data list."

        if success: self.sys_log(msg, "#10B981")
        else: self.sys_log(msg or "Interpreter: Semantic Mismatch.", "#EF4444")

if __name__ == "__main__":
    app = QApplication(sys.argv); app.setStyle("Fusion")
    win = NeuroShellOS(); win.show(); sys.exit(app.exec())