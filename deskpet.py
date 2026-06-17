#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
Pixel DeskPet

A small PyQt5 desktop companion with selectable pixel pets, smooth behaviors,
reminders, and persistent settings.
"""

import json
import math
import os
import random
import sys
import time
from dataclasses import dataclass
from datetime import datetime, timedelta

from PyQt5.QtCore import QPoint, QRect, QRectF, Qt, QTimer
from PyQt5.QtGui import QColor, QCursor, QFont, QPainter, QPen
from PyQt5.QtWidgets import (
    QAction,
    QActionGroup,
    QApplication,
    QCheckBox,
    QDialog,
    QFormLayout,
    QHBoxLayout,
    QLabel,
    QMainWindow,
    QMenu,
    QPushButton,
    QSlider,
    QSpinBox,
    QVBoxLayout,
    QWidget,
)


APP_DIR = os.path.dirname(os.path.abspath(__file__))
SETTINGS_FILE = os.path.join(APP_DIR, "deskpet_settings.json")
MESSAGE_FILE = os.path.join(APP_DIR, "deskpet_message.json")


DEFAULT_SETTINGS = {
    "pet": "cat",
    "accessory": "scarf",
    "pet_size": 188,
    "opacity": 0.96,
    "x": -1,
    "y": -1,
    "remind_enabled": True,
    "show_status": True,
    "wander_enabled": True,
    "quiet_mode": False,
    "animation_speed": 130,
    "break_interval_min": 45,
    "water_interval_min": 30,
}


def load_settings():
    try:
        with open(SETTINGS_FILE, "r", encoding="utf-8") as handle:
            data = json.load(handle)
            return {**DEFAULT_SETTINGS, **data}
    except Exception:
        return dict(DEFAULT_SETTINGS)


def save_settings(settings):
    try:
        with open(SETTINGS_FILE, "w", encoding="utf-8") as handle:
            json.dump(settings, handle, ensure_ascii=False, indent=2)
    except Exception:
        pass


CODEX_EVENT_PRESETS = {
    "thinking": {
        "mood": "thinking",
        "duration": 180000,
        "sticky": True,
        "phrases": [
            "Codex 正在思考中，请耐心等待",
            "我在旁边盯着进度，有结果马上告诉你",
            "正在拆解需求，先别急",
            "脑袋高速运转中",
        ],
    },
    "working": {
        "mood": "working",
        "duration": 180000,
        "sticky": True,
        "phrases": [
            "Codex 正在动手处理",
            "正在改文件和检查细节",
            "我会在完成后第一时间提醒你",
            "处理中，请稍等一下",
        ],
    },
    "done": {
        "mood": "happy",
        "duration": 8200,
        "sticky": False,
        "phrases": [
            "哇！Codex 帮你搞定刚刚提出的需求了，请查收！",
            "完成啦，快看看效果",
            "需求已经处理好，请验收",
            "我把好消息带来啦，任务完成",
        ],
    },
    "waiting": {
        "mood": "stretch",
        "duration": 14000,
        "sticky": False,
        "phrases": [
            "Codex 需要你确认一下下一步",
            "这里有个选择需要你拍板",
            "先暂停一下，等你确认",
        ],
    },
    "error": {
        "mood": "hungry",
        "duration": 12000,
        "sticky": False,
        "phrases": [
            "遇到一点问题，Codex 已经把原因写出来了",
            "这一步没跑通，需要看一下提示",
            "我这边卡住了，等你看下错误信息",
        ],
    },
}


def write_pet_message(text="", mood=None, duration=None, event=None):
    preset = CODEX_EVENT_PRESETS.get(event or "")
    if preset:
        phrases = preset["phrases"]
        text = str(text).strip() or random.choice(phrases)
        mood = mood or preset["mood"]
        duration = int(duration or preset["duration"])
        sticky = bool(preset["sticky"])
    else:
        text = str(text).strip()
        mood = mood or "happy"
        duration = int(duration or 5600)
        sticky = False
        phrases = []

    message = {
        "id": f"{time.time():.6f}",
        "text": text,
        "mood": mood,
        "duration": duration,
        "event": event or "say",
        "sticky": sticky,
        "phrases": phrases,
        "created_at": time.time(),
    }
    temp_file = f"{MESSAGE_FILE}.tmp"
    with open(temp_file, "w", encoding="utf-8") as handle:
        json.dump(message, handle, ensure_ascii=False, indent=2)
    os.replace(temp_file, MESSAGE_FILE)
    return message


@dataclass(frozen=True)
class PetTheme:
    key: str
    name: str
    tagline: str
    species: str
    body: QColor
    body_dark: QColor
    highlight: QColor
    outline: QColor
    cheek: QColor
    accent: QColor
    belly: QColor
    accessory: QColor


PETS = {
    "cat": PetTheme(
        "cat",
        "奶茶猫",
        "温柔、黏人、会提醒你休息",
        "cat",
        QColor("#f0c98d"),
        QColor("#d79b5d"),
        QColor("#ffe7bc"),
        QColor("#3a2a22"),
        QColor("#ff9fb2"),
        QColor("#8f5a36"),
        QColor("#ffe2b5"),
        QColor("#4f8fdd"),
    ),
    "dog": PetTheme(
        "dog",
        "焦糖柴犬",
        "元气、可靠、适合陪工位",
        "dog",
        QColor("#d98a4b"),
        QColor("#9b5730"),
        QColor("#f4b06d"),
        QColor("#35231d"),
        QColor("#ff9f8d"),
        QColor("#fff0d2"),
        QColor("#ffe4bf"),
        QColor("#ef5d4a"),
    ),
    "fox": PetTheme(
        "fox",
        "赤焰狐",
        "聪明、灵动、动作更俏皮",
        "fox",
        QColor("#e86832"),
        QColor("#a53c25"),
        QColor("#ff9b58"),
        QColor("#321f1a"),
        QColor("#ff9f88"),
        QColor("#f8f0d8"),
        QColor("#fff3da"),
        QColor("#293462"),
    ),
    "rabbit": PetTheme(
        "rabbit",
        "月光兔",
        "安静、治愈、适合轻提醒",
        "rabbit",
        QColor("#e8e8f2"),
        QColor("#b8bbd1"),
        QColor("#ffffff"),
        QColor("#34364d"),
        QColor("#ff9fc6"),
        QColor("#f5b6d6"),
        QColor("#ffffff"),
        QColor("#8d7bdc"),
    ),
    "slime": PetTheme(
        "slime",
        "薄荷史莱姆",
        "软弹、清爽、表情很明显",
        "slime",
        QColor("#55d6be"),
        QColor("#239c92"),
        QColor("#9dffe9"),
        QColor("#173d3d"),
        QColor("#ff93aa"),
        QColor("#dbfff7"),
        QColor("#b9fff1"),
        QColor("#ffcf5a"),
    ),
}


MOOD_TEXT = {
    "idle": "发呆中",
    "happy": "开心",
    "walk": "散步",
    "sleep": "睡觉",
    "hungry": "想吃点东西",
    "thirsty": "该喝水啦",
    "stretch": "伸懒腰",
    "love": "被摸头",
    "focus": "专注陪伴",
    "thinking": "思考中",
    "working": "处理中",
}


ACCESSORIES = {
    "none": "无配饰",
    "scarf": "小围巾",
    "bow": "蝴蝶结",
    "crown": "小王冠",
}


class PixelPainter:
    def __init__(self, painter, cell, ox, oy):
        self.painter = painter
        self.cell = cell
        self.ox = ox
        self.oy = oy

    def rect(self, x, y, w, h, color):
        self.painter.fillRect(
            QRectF(
                self.ox + x * self.cell,
                self.oy + y * self.cell,
                w * self.cell,
                h * self.cell,
            ),
            color,
        )

    def line(self, x, y, w, color):
        self.rect(x, y, w, 1, color)


class PetCanvas(QWidget):
    def __init__(self, owner):
        super().__init__(owner)
        self.owner = owner
        self.setAttribute(Qt.WA_TranslucentBackground)

    def paintEvent(self, event):
        painter = QPainter(self)
        painter.setRenderHint(QPainter.Antialiasing, False)
        painter.setPen(Qt.NoPen)
        self.owner.draw_pet(painter, self.rect())


class SettingsDialog(QDialog):
    def __init__(self, parent):
        super().__init__(parent)
        self.parent_pet = parent
        self.setWindowTitle("桌面宠物设置")
        self.setModal(True)
        self.setMinimumWidth(360)

        layout = QVBoxLayout(self)
        form = QFormLayout()

        self.size_slider = QSlider(Qt.Horizontal)
        self.size_slider.setRange(112, 320)
        self.size_slider.setValue(parent.settings["pet_size"])
        self.size_value = QLabel(str(parent.settings["pet_size"]))
        size_row = QHBoxLayout()
        size_row.addWidget(self.size_slider)
        size_row.addWidget(self.size_value)
        form.addRow("大小", size_row)

        self.opacity_slider = QSlider(Qt.Horizontal)
        self.opacity_slider.setRange(35, 100)
        self.opacity_slider.setValue(int(parent.settings["opacity"] * 100))
        self.opacity_value = QLabel(f"{int(parent.settings['opacity'] * 100)}%")
        opacity_row = QHBoxLayout()
        opacity_row.addWidget(self.opacity_slider)
        opacity_row.addWidget(self.opacity_value)
        form.addRow("透明度", opacity_row)

        self.remind_check = QCheckBox("启用喝水和休息提醒")
        self.remind_check.setChecked(parent.settings["remind_enabled"])
        form.addRow("", self.remind_check)

        self.status_check = QCheckBox("显示心情 / 精力 / 饱腹状态条")
        self.status_check.setChecked(parent.settings["show_status"])
        form.addRow("", self.status_check)

        self.wander_check = QCheckBox("允许宠物自动散步")
        self.wander_check.setChecked(parent.settings["wander_enabled"])
        form.addRow("", self.wander_check)

        self.quiet_check = QCheckBox("勿扰模式：只保留气泡，不主动提醒")
        self.quiet_check.setChecked(parent.settings["quiet_mode"])
        form.addRow("", self.quiet_check)

        self.speed_slider = QSlider(Qt.Horizontal)
        self.speed_slider.setRange(70, 220)
        self.speed_slider.setValue(parent.settings["animation_speed"])
        self.speed_value = QLabel(f"{parent.settings['animation_speed']} ms")
        speed_row = QHBoxLayout()
        speed_row.addWidget(self.speed_slider)
        speed_row.addWidget(self.speed_value)
        form.addRow("动画速度", speed_row)

        self.water_spin = QSpinBox()
        self.water_spin.setRange(5, 240)
        self.water_spin.setValue(parent.settings["water_interval_min"])
        self.water_spin.setSuffix(" 分钟")
        form.addRow("喝水间隔", self.water_spin)

        self.break_spin = QSpinBox()
        self.break_spin.setRange(10, 240)
        self.break_spin.setValue(parent.settings["break_interval_min"])
        self.break_spin.setSuffix(" 分钟")
        form.addRow("休息间隔", self.break_spin)

        layout.addLayout(form)

        button_row = QHBoxLayout()
        reset_btn = QPushButton("重置位置")
        cancel_btn = QPushButton("取消")
        save_btn = QPushButton("保存")
        save_btn.setDefault(True)
        button_row.addWidget(reset_btn)
        button_row.addStretch()
        button_row.addWidget(cancel_btn)
        button_row.addWidget(save_btn)
        layout.addLayout(button_row)

        self.size_slider.valueChanged.connect(
            lambda value: self.size_value.setText(str(value))
        )
        self.opacity_slider.valueChanged.connect(
            lambda value: self.opacity_value.setText(f"{value}%")
        )
        self.speed_slider.valueChanged.connect(
            lambda value: self.speed_value.setText(f"{value} ms")
        )
        cancel_btn.clicked.connect(self.reject)
        reset_btn.clicked.connect(self.reset_position)
        save_btn.clicked.connect(self.save)

    def reset_position(self):
        screen = QApplication.primaryScreen().availableGeometry()
        size = self.parent_pet.settings["pet_size"]
        self.parent_pet.move(screen.right() - size - 40, screen.bottom() - size - 48)
        self.parent_pet.persist_position()

    def save(self):
        self.parent_pet.settings["pet_size"] = self.size_slider.value()
        self.parent_pet.settings["opacity"] = self.opacity_slider.value() / 100
        self.parent_pet.settings["remind_enabled"] = self.remind_check.isChecked()
        self.parent_pet.settings["show_status"] = self.status_check.isChecked()
        self.parent_pet.settings["wander_enabled"] = self.wander_check.isChecked()
        self.parent_pet.settings["quiet_mode"] = self.quiet_check.isChecked()
        self.parent_pet.settings["animation_speed"] = self.speed_slider.value()
        self.parent_pet.settings["water_interval_min"] = self.water_spin.value()
        self.parent_pet.settings["break_interval_min"] = self.break_spin.value()
        self.parent_pet.apply_settings()
        self.parent_pet.schedule_reminders(reset=True)
        save_settings(self.parent_pet.settings)
        self.accept()


class DeskPet(QMainWindow):
    def __init__(self):
        super().__init__()
        self.settings = load_settings()
        if self.settings["pet"] not in PETS:
            self.settings["pet"] = "cat"

        self.theme = PETS[self.settings["pet"]]
        self.mood = "idle"
        self.frame = 0
        self.facing = 1
        self.dragging = False
        self.drag_offset = QPoint()
        self.happiness = 78
        self.energy = 72
        self.fullness = 68
        self.bubble_text = ""
        self.bubble_until = datetime.min
        self.last_interaction = datetime.now()
        self.next_water = datetime.now()
        self.next_break = datetime.now()
        self.walk_steps = 0
        self.walk_dx = 1
        self.focus_until = datetime.min
        self.last_message_id = None
        self.active_event = None
        self.active_event_until = datetime.min
        self.active_event_phrases = []
        self.active_event_index = 0
        self.next_event_phrase_at = datetime.min

        self.setWindowFlags(
            Qt.FramelessWindowHint
            | Qt.WindowStaysOnTopHint
            | Qt.Tool
            | Qt.NoDropShadowWindowHint
        )
        self.setAttribute(Qt.WA_TranslucentBackground)
        self.setMouseTracking(True)

        self.canvas = PetCanvas(self)
        self.setCentralWidget(self.canvas)

        self.tick_timer = QTimer(self)
        self.tick_timer.timeout.connect(self.tick)
        self.tick_timer.start(130)

        self.behavior_timer = QTimer(self)
        self.behavior_timer.timeout.connect(self.choose_behavior)
        self.behavior_timer.start(3600)

        self.reminder_timer = QTimer(self)
        self.reminder_timer.timeout.connect(self.check_reminders)
        self.reminder_timer.start(1000)

        self.message_timer = QTimer(self)
        self.message_timer.timeout.connect(self.check_external_message)
        self.message_timer.start(650)

        self.codex_event_timer = QTimer(self)
        self.codex_event_timer.timeout.connect(self.tick_codex_event)
        self.codex_event_timer.start(1600)

        self.apply_settings(initial=True)
        self.schedule_reminders(reset=True)
        self.place_window()
        self.say(f"{self.theme.name} 已上线", 2200)

    def apply_settings(self, initial=False):
        size = int(self.settings["pet_size"])
        self.resize(size, int(size * 1.18))
        self.setWindowOpacity(float(self.settings["opacity"]))
        self.tick_timer.setInterval(int(self.settings["animation_speed"]))
        if not initial:
            self.canvas.update()

    def place_window(self):
        x = int(self.settings.get("x", -1))
        y = int(self.settings.get("y", -1))
        screen = QApplication.primaryScreen().availableGeometry()
        if x < 0 or y < 0:
            x = screen.right() - self.width() - 40
            y = screen.bottom() - self.height() - 40
        x = max(screen.left(), min(x, screen.right() - self.width()))
        y = max(screen.top(), min(y, screen.bottom() - self.height()))
        self.move(x, y)

    def persist_position(self):
        self.settings["x"] = self.x()
        self.settings["y"] = self.y()
        save_settings(self.settings)

    def schedule_reminders(self, reset=False):
        now = datetime.now()
        if reset or self.next_water <= now:
            self.next_water = now + timedelta(
                minutes=int(self.settings["water_interval_min"])
            )
        if reset or self.next_break <= now:
            self.next_break = now + timedelta(
                minutes=int(self.settings["break_interval_min"])
            )

    def say(self, text, duration=2600):
        self.bubble_text = str(text).strip()
        self.bubble_until = datetime.now() + timedelta(milliseconds=duration)
        self.canvas.update()

    def set_mood(self, mood, duration_hint=True):
        self.mood = mood
        if duration_hint:
            self.say(MOOD_TEXT.get(mood, mood), 1800)
        self.canvas.update()

    def tick(self):
        self.frame += 1
        if self.mood == "focus" and datetime.now() >= self.focus_until:
            self.set_mood("happy", False)
            self.say("专注结束，休息一下", 3600)
        if self.frame % 35 == 0:
            self.happiness = max(0, self.happiness - 1)
            self.energy = max(0, self.energy - 1)
            self.fullness = max(0, self.fullness - 1)

        if self.mood == "walk":
            self.walk_pet()
        elif self.mood == "sleep" and self.frame % 45 == 0:
            self.energy = min(100, self.energy + 3)

        if self.fullness < 25 and self.mood not in ("sleep", "hungry"):
            self.set_mood("hungry", False)
        if self.energy < 18 and self.mood != "sleep":
            self.set_mood("sleep", False)

        self.canvas.update()

    def choose_behavior(self):
        if self.dragging:
            return
        if self.mood in ("focus", "thinking", "working"):
            return
        idle_seconds = (datetime.now() - self.last_interaction).total_seconds()
        if idle_seconds > 90 and self.energy < 65:
            self.set_mood("sleep")
            return

        options = ["idle", "idle", "happy", "stretch"]
        if self.settings["wander_enabled"]:
            options.append("walk")
        if self.energy < 40:
            options.append("sleep")
        self.set_mood(random.choice(options), False)
        if self.mood == "walk":
            self.walk_steps = random.randint(18, 46)
            self.walk_dx = random.choice([-1, 1])
            self.facing = self.walk_dx

    def walk_pet(self):
        if self.walk_steps <= 0:
            self.set_mood("idle", False)
            return
        screen = QApplication.primaryScreen().availableGeometry()
        nx = self.x() + self.walk_dx * 3
        if nx < screen.left() or nx + self.width() > screen.right():
            self.walk_dx *= -1
            self.facing = self.walk_dx
            nx = self.x() + self.walk_dx * 3
        self.move(nx, self.y())
        self.walk_steps -= 1
        if self.walk_steps <= 0:
            self.persist_position()

    def check_reminders(self):
        if not self.settings["remind_enabled"] or self.settings["quiet_mode"]:
            return
        now = datetime.now()
        if now >= self.next_water:
            self.set_mood("thirsty")
            self.say("喝口水，别硬撑", 5200)
            self.next_water = now + timedelta(
                minutes=int(self.settings["water_interval_min"])
            )
        if now >= self.next_break:
            self.set_mood("stretch")
            self.say("起来活动 2 分钟", 5200)
            self.next_break = now + timedelta(
                minutes=int(self.settings["break_interval_min"])
            )

    def check_external_message(self):
        if not os.path.exists(MESSAGE_FILE):
            return
        try:
            with open(MESSAGE_FILE, "r", encoding="utf-8") as handle:
                message = json.load(handle)
        except Exception:
            return

        message_id = message.get("id")
        text = str(message.get("text", "")).strip()
        if not message_id or message_id == self.last_message_id or not text:
            return

        self.last_message_id = message_id
        mood = message.get("mood", "happy")
        if mood in MOOD_TEXT:
            self.set_mood(mood, False)
        else:
            self.set_mood("happy", False)
        self.configure_codex_event(message)
        self.happiness = min(100, self.happiness + 8)
        self.energy = min(100, self.energy + 2)
        self.last_interaction = datetime.now()
        duration = int(message.get("duration", 5600))
        bubble_duration = max(1800, min(duration, 18000))
        self.say(text, bubble_duration)

    def configure_codex_event(self, message):
        if message.get("sticky"):
            duration = int(message.get("duration", 180000))
            self.active_event = message.get("event", "working")
            self.active_event_until = datetime.now() + timedelta(
                milliseconds=max(5000, duration)
            )
            phrases = message.get("phrases") or []
            self.active_event_phrases = [str(phrase) for phrase in phrases if phrase]
            self.active_event_index = 0
            self.next_event_phrase_at = datetime.now() + timedelta(milliseconds=5200)
        else:
            self.clear_codex_event()

    def clear_codex_event(self):
        self.active_event = None
        self.active_event_until = datetime.min
        self.active_event_phrases = []
        self.active_event_index = 0
        self.next_event_phrase_at = datetime.min

    def tick_codex_event(self):
        if not self.active_event:
            return
        now = datetime.now()
        if now >= self.active_event_until:
            self.clear_codex_event()
            if self.mood in ("thinking", "working"):
                self.set_mood("idle", False)
            return
        if self.active_event_phrases and now >= self.next_event_phrase_at:
            phrase = self.active_event_phrases[
                self.active_event_index % len(self.active_event_phrases)
            ]
            self.active_event_index += 1
            self.next_event_phrase_at = now + timedelta(milliseconds=6200)
            self.say(phrase, 4300)

    def feed(self):
        self.fullness = min(100, self.fullness + 28)
        self.happiness = min(100, self.happiness + 10)
        self.energy = min(100, self.energy + 4)
        self.last_interaction = datetime.now()
        self.set_mood("happy", False)
        self.say("好吃", 2200)

    def pet_head(self):
        self.happiness = min(100, self.happiness + 16)
        self.energy = min(100, self.energy + 2)
        self.last_interaction = datetime.now()
        self.set_mood("love", False)
        self.say("舒服", 2200)

    def play(self):
        self.happiness = min(100, self.happiness + 24)
        self.energy = max(0, self.energy - 8)
        self.fullness = max(0, self.fullness - 4)
        self.last_interaction = datetime.now()
        self.set_mood("happy", False)
        self.say("再来一次", 2200)

    def sleep(self):
        self.energy = min(100, self.energy + 18)
        self.last_interaction = datetime.now()
        self.set_mood("sleep", False)
        self.say("晚安", 2200)

    def drink_done(self):
        self.last_interaction = datetime.now()
        self.next_water = datetime.now() + timedelta(
            minutes=int(self.settings["water_interval_min"])
        )
        self.set_mood("happy", False)
        self.say("补水完成", 2000)

    def focus_mode(self, minutes=25):
        self.focus_until = datetime.now() + timedelta(minutes=minutes)
        self.energy = min(100, self.energy + 6)
        self.last_interaction = datetime.now()
        self.set_mood("focus", False)
        self.say(f"陪你专注 {minutes} 分钟", 3200)

    def reset_stats(self):
        self.happiness = 78
        self.energy = 72
        self.fullness = 68
        self.set_mood("happy", False)
        self.say("状态已恢复", 2200)

    def switch_pet(self, key):
        self.settings["pet"] = key
        self.theme = PETS[key]
        save_settings(self.settings)
        self.set_mood("happy", False)
        self.say(f"切换为 {self.theme.name}", 2600)

    def switch_accessory(self, key):
        self.settings["accessory"] = key
        save_settings(self.settings)
        self.set_mood("happy", False)
        self.say(ACCESSORIES[key], 2200)

    def simulate_codex_event(self, event):
        message = write_pet_message(event=event)
        self.last_message_id = None
        self.say(message["text"], min(int(message["duration"]), 9000))

    def contextMenuEvent(self, event):
        menu = QMenu(self)
        menu.setStyleSheet(
            """
            QMenu {
                background: #232323;
                color: #f4f4f4;
                border: 1px solid #494949;
                padding: 6px;
                font-size: 13px;
            }
            QMenu::item { padding: 7px 26px 7px 16px; }
            QMenu::item:selected { background: #3f6f68; }
            QMenu::separator { height: 1px; background: #444; margin: 5px 2px; }
            """
        )

        title = QAction(f"{self.theme.name} · {MOOD_TEXT.get(self.mood, self.mood)}", self)
        title.setEnabled(False)
        menu.addAction(title)
        subtitle = QAction(self.theme.tagline, self)
        subtitle.setEnabled(False)
        menu.addAction(subtitle)
        menu.addSeparator()

        pet_menu = menu.addMenu("选择宠物")
        group = QActionGroup(self)
        for key, theme in PETS.items():
            action = QAction(theme.name, self, checkable=True)
            action.setChecked(key == self.theme.key)
            action.triggered.connect(lambda checked, pet_key=key: self.switch_pet(pet_key))
            group.addAction(action)
            pet_menu.addAction(action)

        accessory_menu = menu.addMenu("配饰")
        accessory_group = QActionGroup(self)
        for key, label in ACCESSORIES.items():
            action = QAction(label, self, checkable=True)
            action.setChecked(key == self.settings["accessory"])
            action.triggered.connect(
                lambda checked, accessory_key=key: self.switch_accessory(accessory_key)
            )
            accessory_group.addAction(action)
            accessory_menu.addAction(action)

        menu.addSeparator()
        status = QAction(
            f"心情 {self.happiness}%  精力 {self.energy}%  饱腹 {self.fullness}%",
            self,
        )
        status.setEnabled(False)
        menu.addAction(status)
        menu.addSeparator()

        action_pet = menu.addAction("摸头")
        action_feed = menu.addAction("喂食")
        action_play = menu.addAction("玩耍")
        action_sleep = menu.addAction("睡觉")
        action_water = menu.addAction("我喝水了")
        focus_menu = menu.addMenu("专注陪伴")
        action_focus_25 = focus_menu.addAction("25 分钟")
        action_focus_45 = focus_menu.addAction("45 分钟")
        codex_menu = menu.addMenu("Codex 联动演示")
        action_thinking = codex_menu.addAction("正在思考")
        action_working = codex_menu.addAction("正在处理")
        action_done = codex_menu.addAction("完成提醒")
        action_waiting = codex_menu.addAction("等待确认")
        menu.addSeparator()
        action_reset_stats = menu.addAction("恢复状态")
        action_settings = menu.addAction("设置")
        action_quit = menu.addAction("退出")

        action_pet.triggered.connect(self.pet_head)
        action_feed.triggered.connect(self.feed)
        action_play.triggered.connect(self.play)
        action_sleep.triggered.connect(self.sleep)
        action_water.triggered.connect(self.drink_done)
        action_focus_25.triggered.connect(lambda: self.focus_mode(25))
        action_focus_45.triggered.connect(lambda: self.focus_mode(45))
        action_thinking.triggered.connect(lambda: self.simulate_codex_event("thinking"))
        action_working.triggered.connect(lambda: self.simulate_codex_event("working"))
        action_done.triggered.connect(lambda: self.simulate_codex_event("done"))
        action_waiting.triggered.connect(lambda: self.simulate_codex_event("waiting"))
        action_reset_stats.triggered.connect(self.reset_stats)
        action_settings.triggered.connect(self.open_settings)
        action_quit.triggered.connect(self.close)
        menu.exec_(event.globalPos())

    def open_settings(self):
        SettingsDialog(self).exec_()

    def mousePressEvent(self, event):
        if event.button() == Qt.LeftButton:
            self.dragging = True
            self.drag_offset = event.globalPos() - self.frameGeometry().topLeft()
            self.last_interaction = datetime.now()
            self.setCursor(QCursor(Qt.ClosedHandCursor))
            event.accept()

    def mouseMoveEvent(self, event):
        if self.dragging and event.buttons() & Qt.LeftButton:
            self.move(event.globalPos() - self.drag_offset)
            event.accept()

    def mouseReleaseEvent(self, event):
        if event.button() == Qt.LeftButton and self.dragging:
            self.dragging = False
            self.setCursor(QCursor(Qt.ArrowCursor))
            self.persist_position()
            event.accept()

    def mouseDoubleClickEvent(self, event):
        if event.button() == Qt.LeftButton:
            self.pet_head()
            event.accept()

    def closeEvent(self, event):
        self.persist_position()
        event.accept()

    def draw_pet(self, painter, rect):
        painter.setPen(Qt.NoPen)
        s = min(rect.width(), int(rect.height() * 0.86))
        cell = max(3, s // 28)
        sprite_w = cell * 28
        sprite_h = cell * 28
        ox = (rect.width() - sprite_w) / 2
        oy = rect.height() - sprite_h - cell * 1.2

        if self.mood == "walk":
            oy += math.sin(self.frame / 2.2) * cell * 0.7
        elif self.mood == "happy":
            oy += math.sin(self.frame / 1.8) * cell * 0.8
        elif self.mood == "sleep":
            oy += cell * 1.2
        elif self.mood == "stretch":
            oy -= abs(math.sin(self.frame / 4.0)) * cell * 1.2

        px = PixelPainter(painter, cell, ox, oy)
        self.draw_shadow(px)
        if self.theme.species == "slime":
            self.draw_slime(px)
        else:
            self.draw_animal(px)
        if self.settings["show_status"]:
            self.draw_status_bar(painter, rect)
        self.draw_activity_badge(painter, rect)
        self.draw_bubble(painter, rect)

    def draw_shadow(self, px):
        shadow = QColor(0, 0, 0, 48)
        px.rect(7, 26, 14, 1, shadow)
        px.rect(9, 27, 10, 1, shadow)

    def draw_animal(self, px):
        t = self.theme
        eye_y = 12
        blink = self.frame % 46 in (0, 1, 2)
        sleeping = self.mood == "sleep"
        happy = self.mood in ("happy", "love")
        focused = self.mood in ("focus", "thinking", "working")
        walk_phase = (self.frame // 3) % 2

        if t.species == "rabbit":
            px.rect(7, 1, 4, 9, t.outline)
            px.rect(17, 1, 4, 9, t.outline)
            px.rect(8, 2, 2, 7, t.body)
            px.rect(18, 2, 2, 7, t.body)
            px.rect(9, 3, 1, 5, t.accent)
            px.rect(18, 3, 1, 5, t.accent)
        elif t.species == "fox":
            px.rect(4, 5, 5, 7, t.outline)
            px.rect(19, 5, 5, 7, t.outline)
            px.rect(5, 6, 3, 5, t.body)
            px.rect(20, 6, 3, 5, t.body)
            px.rect(6, 8, 2, 2, t.accent)
            px.rect(20, 8, 2, 2, t.accent)
        else:
            px.rect(5, 6, 5, 5, t.outline)
            px.rect(18, 6, 5, 5, t.outline)
            px.rect(6, 7, 3, 4, t.body)
            px.rect(19, 7, 3, 4, t.body)
            if t.species == "dog":
                px.rect(4, 8, 4, 5, t.body_dark)
                px.rect(20, 8, 4, 5, t.body_dark)

        px.rect(6, 8, 16, 2, t.outline)
        px.rect(4, 10, 20, 11, t.outline)
        px.rect(5, 9, 18, 11, t.body)
        px.rect(7, 10, 7, 1, t.highlight)
        px.rect(6, 11, 3, 1, t.highlight)
        px.rect(18, 10, 3, 1, t.body_dark)
        px.rect(20, 12, 2, 5, t.body_dark)
        px.rect(6, 20, 16, 4, t.outline)
        px.rect(7, 20, 14, 4, t.body)
        px.rect(9, 18, 10, 6, t.belly)
        px.rect(11, 19, 6, 1, QColor(255, 255, 255, 90))
        px.rect(6, 15, 3, 2, t.cheek)
        px.rect(19, 15, 3, 2, t.cheek)

        if t.species == "fox":
            px.rect(11, 14, 6, 5, t.belly)
            px.rect(7, 10, 3, 2, t.body_dark)
            px.rect(18, 10, 3, 2, t.body_dark)
            px.rect(13, 16, 2, 1, t.outline)
        elif t.species == "dog":
            px.rect(12, 14, 4, 3, t.accent)
            px.rect(5, 10, 4, 3, t.body_dark)
            px.rect(19, 10, 4, 3, t.body_dark)
            px.rect(13, 16, 2, 1, t.outline)
        elif t.species == "rabbit":
            px.rect(12, 15, 4, 2, QColor("#f5c7dd"))
            px.rect(13, 14, 2, 2, t.accent)
        else:
            px.rect(13, 14, 2, 2, t.accent)

        if sleeping:
            px.line(9, eye_y, 4, t.outline)
            px.line(16, eye_y, 4, t.outline)
            self.draw_sleep_marks(px)
        elif self.mood == "love":
            px.rect(9, eye_y, 2, 1, t.cheek)
            px.rect(10, eye_y + 1, 1, 1, t.cheek)
            px.rect(16, eye_y, 2, 1, t.cheek)
            px.rect(17, eye_y + 1, 1, 1, t.cheek)
            px.line(12, 16, 4, t.outline)
        elif happy:
            px.rect(9, eye_y, 1, 1, t.outline)
            px.rect(10, eye_y + 1, 1, 1, t.outline)
            px.rect(11, eye_y, 1, 1, t.outline)
            px.rect(16, eye_y, 1, 1, t.outline)
            px.rect(17, eye_y + 1, 1, 1, t.outline)
            px.rect(18, eye_y, 1, 1, t.outline)
            px.line(12, 16, 4, t.outline)
        elif focused:
            px.line(9, eye_y, 4, t.outline)
            px.rect(11, eye_y + 1, 1, 1, t.outline)
            px.line(16, eye_y, 4, t.outline)
            px.rect(16, eye_y + 1, 1, 1, t.outline)
            px.line(12, 16, 4, t.outline)
        elif blink:
            px.line(9, eye_y + 1, 4, t.outline)
            px.line(16, eye_y + 1, 4, t.outline)
        else:
            px.rect(9, eye_y, 3, 3, t.outline)
            px.rect(16, eye_y, 3, 3, t.outline)
            px.rect(10, eye_y, 1, 1, QColor("#ffffff"))
            px.rect(17, eye_y, 1, 1, QColor("#ffffff"))
            px.rect(13, 16, 2, 1, t.outline)

        if t.species == "cat":
            px.rect(6, 14, 1, 1, t.outline)
            px.rect(21, 14, 1, 1, t.outline)
            px.rect(7, 16, 1, 1, t.outline)
            px.rect(20, 16, 1, 1, t.outline)
            px.rect(8, 10, 2, 1, t.accent)
            px.rect(18, 10, 2, 1, t.accent)

        if t.species == "fox":
            tail_y = 18 + (1 if self.mood == "happy" and (self.frame // 5) % 2 else 0)
            px.rect(20, tail_y, 7, 4, t.outline)
            px.rect(21, tail_y - 1, 5, 4, t.body)
            px.rect(25, tail_y - 1, 2, 3, t.accent)
        elif t.species == "dog":
            tail_y = 19 - (1 if self.mood == "happy" and (self.frame // 4) % 2 else 0)
            px.rect(21, tail_y, 5, 2, t.outline)
            px.rect(22, tail_y - 1, 3, 2, t.body_dark)
        elif t.species == "rabbit":
            px.rect(21, 20, 2, 2, t.outline)
            px.rect(22, 20, 1, 1, t.belly)
        else:
            tail_y = 18 + (1 if self.mood == "happy" and (self.frame // 5) % 2 else 0)
            px.rect(21, tail_y, 5, 3, t.outline)
            px.rect(22, tail_y - 1, 3, 3, t.body)

        foot_offset = 1 if self.mood == "walk" and walk_phase else 0
        px.rect(8, 24 + foot_offset, 5, 2, t.outline)
        px.rect(16, 25 - foot_offset, 5, 2, t.outline)
        px.rect(9, 24 + foot_offset, 3, 1, t.body_dark)
        px.rect(17, 25 - foot_offset, 3, 1, t.body_dark)
        self.draw_accessory(px)

    def draw_accessory(self, px):
        accessory = self.settings.get("accessory", "scarf")
        if accessory == "none":
            return
        t = self.theme
        if accessory == "scarf":
            px.rect(7, 18, 14, 2, t.outline)
            px.rect(8, 18, 12, 1, t.accessory)
            px.rect(18, 19, 3, 3, t.outline)
            px.rect(19, 20, 2, 2, t.accessory)
            px.rect(10, 18, 1, 1, QColor("#ffffff"))
        elif accessory == "bow":
            px.rect(11, 7, 2, 2, t.outline)
            px.rect(15, 7, 2, 2, t.outline)
            px.rect(13, 8, 2, 2, t.outline)
            px.rect(10, 6, 3, 2, t.accessory)
            px.rect(15, 6, 3, 2, t.accessory)
            px.rect(13, 8, 2, 1, QColor("#ffffff"))
        elif accessory == "crown":
            gold = QColor("#ffd75a")
            px.rect(10, 5, 8, 2, t.outline)
            px.rect(10, 3, 2, 4, t.outline)
            px.rect(13, 2, 2, 5, t.outline)
            px.rect(16, 3, 2, 4, t.outline)
            px.rect(11, 5, 6, 1, gold)
            px.rect(11, 4, 1, 1, gold)
            px.rect(14, 3, 1, 2, gold)
            px.rect(16, 4, 1, 1, gold)

    def draw_slime(self, px):
        t = self.theme
        blink = self.frame % 48 in (0, 1, 2)
        happy = self.mood in ("happy", "love")
        focused = self.mood in ("focus", "thinking", "working")
        sleeping = self.mood == "sleep"
        squash = 1 if self.mood == "walk" and (self.frame // 4) % 2 else 0

        px.rect(11, 6 + squash, 6, 2, t.outline)
        px.rect(12, 5 + squash, 4, 2, t.body)
        px.rect(8, 8 + squash, 12, 2, t.outline)
        px.rect(5, 10 + squash, 18, 3, t.outline)
        px.rect(3, 13 + squash, 22, 8, t.outline)
        px.rect(4, 12 + squash, 20, 9, t.body)
        px.rect(6, 10 + squash, 16, 4, t.body)
        px.rect(8, 9 + squash, 12, 2, t.body)
        px.rect(8, 18 + squash, 12, 4, t.belly)
        px.rect(6, 12 + squash, 7, 1, t.highlight)
        px.rect(7, 13 + squash, 3, 1, t.highlight)
        px.rect(19, 14 + squash, 3, 5, t.body_dark)
        px.rect(7, 15 + squash, 3, 2, t.cheek)
        px.rect(18, 15 + squash, 3, 2, t.cheek)
        px.rect(9, 11 + squash, 3, 1, t.accent)

        if sleeping:
            px.line(9, 14 + squash, 4, t.outline)
            px.line(16, 14 + squash, 4, t.outline)
            self.draw_sleep_marks(px)
        elif self.mood == "love":
            px.rect(9, 14 + squash, 2, 1, t.cheek)
            px.rect(10, 15 + squash, 1, 1, t.cheek)
            px.rect(17, 14 + squash, 2, 1, t.cheek)
            px.rect(18, 15 + squash, 1, 1, t.cheek)
            px.line(12, 17 + squash, 4, t.outline)
        elif happy:
            px.rect(9, 14 + squash, 1, 1, t.outline)
            px.rect(10, 15 + squash, 1, 1, t.outline)
            px.rect(11, 14 + squash, 1, 1, t.outline)
            px.rect(16, 14 + squash, 1, 1, t.outline)
            px.rect(17, 15 + squash, 1, 1, t.outline)
            px.rect(18, 14 + squash, 1, 1, t.outline)
            px.line(12, 17 + squash, 4, t.outline)
        elif focused:
            px.line(9, 14 + squash, 4, t.outline)
            px.rect(11, 15 + squash, 1, 1, t.outline)
            px.line(16, 14 + squash, 4, t.outline)
            px.rect(16, 15 + squash, 1, 1, t.outline)
            px.line(13, 17 + squash, 2, t.outline)
        elif blink:
            px.line(9, 15 + squash, 4, t.outline)
            px.line(16, 15 + squash, 4, t.outline)
        else:
            px.rect(9, 13 + squash, 3, 3, t.outline)
            px.rect(16, 13 + squash, 3, 3, t.outline)
            px.rect(10, 13 + squash, 1, 1, QColor("#ffffff"))
            px.rect(17, 13 + squash, 1, 1, QColor("#ffffff"))
            px.line(13, 17 + squash, 2, t.outline)

        px.rect(6, 22 + squash, 16, 2, t.outline)
        px.rect(7, 21 + squash, 14, 2, t.body_dark)
        self.draw_slime_accessory(px, squash)

    def draw_slime_accessory(self, px, squash):
        accessory = self.settings.get("accessory", "scarf")
        if accessory == "none":
            return
        t = self.theme
        if accessory == "scarf":
            px.rect(7, 18 + squash, 14, 2, t.outline)
            px.rect(8, 18 + squash, 12, 1, t.accessory)
            px.rect(19, 19 + squash, 3, 3, t.outline)
            px.rect(20, 20 + squash, 2, 2, t.accessory)
        elif accessory == "bow":
            px.rect(10, 8 + squash, 3, 2, t.accessory)
            px.rect(15, 8 + squash, 3, 2, t.accessory)
            px.rect(13, 9 + squash, 2, 1, t.outline)
        elif accessory == "crown":
            px.rect(10, 6 + squash, 8, 2, t.outline)
            px.rect(11, 4 + squash, 1, 3, QColor("#ffd75a"))
            px.rect(14, 3 + squash, 1, 4, QColor("#ffd75a"))
            px.rect(17, 4 + squash, 1, 3, QColor("#ffd75a"))

    def draw_sleep_marks(self, px):
        shift = (self.frame // 8) % 3
        color = QColor("#7aa6ff")
        px.rect(22, 5 - shift, 3, 1, color)
        px.rect(24, 4 - shift, 1, 2, color)
        px.rect(23, 8 - shift, 3, 1, color)
        px.rect(25, 7 - shift, 1, 2, color)

    def draw_status_bar(self, painter, rect):
        bar_w = int(rect.width() * 0.58)
        bar_h = max(4, rect.width() // 42)
        x = int((rect.width() - bar_w) / 2)
        y = int(rect.height() - bar_h - 2)
        painter.setPen(Qt.NoPen)
        painter.fillRect(QRect(x, y, bar_w, bar_h), QColor(30, 30, 30, 130))
        colors = [QColor("#f06a8d"), QColor("#ffd166"), QColor("#53d6bd")]
        values = [self.happiness, self.energy, self.fullness]
        segment_w = bar_w // 3
        for index, value in enumerate(values):
            inner_w = max(0, int((segment_w - 2) * value / 100))
            painter.fillRect(
                QRect(x + index * segment_w + 1, y + 1, inner_w, bar_h - 2),
                colors[index],
            )

    def draw_activity_badge(self, painter, rect):
        if self.mood not in ("thinking", "working"):
            return
        cell = max(3, rect.width() // 42)
        x = rect.width() - cell * 9
        y = cell * 3
        painter.setPen(QPen(QColor("#252525"), 2))
        painter.setBrush(QColor(255, 255, 255, 232))
        painter.drawRect(QRectF(x, y, cell * 6, cell * 5))
        painter.setPen(Qt.NoPen)
        accent = QColor("#4f8fdd") if self.mood == "thinking" else QColor("#ffcf5a")
        if self.mood == "thinking":
            dot = (self.frame // 6) % 3
            for index in range(3):
                color = accent if index <= dot else QColor("#b8c3cf")
                painter.fillRect(
                    QRectF(x + cell * (1 + index * 1.5), y + cell * 2, cell, cell),
                    color,
                )
        else:
            painter.fillRect(QRectF(x + cell * 2, y + cell, cell * 2, cell), accent)
            painter.fillRect(QRectF(x + cell, y + cell * 2, cell * 4, cell), accent)
            painter.fillRect(QRectF(x + cell * 2, y + cell * 3, cell * 2, cell), accent)

    def draw_bubble(self, painter, rect):
        if not self.bubble_text or datetime.now() >= self.bubble_until:
            return
        painter.setRenderHint(QPainter.Antialiasing, False)
        font = QFont("Microsoft YaHei UI", max(9, rect.width() // 18))
        font.setBold(True)
        painter.setFont(font)
        metrics = painter.fontMetrics()
        max_text_w = max(88, rect.width() - 34)
        lines = self.wrap_text(metrics, self.bubble_text, max_text_w)
        line_h = metrics.height()
        text_w = max(metrics.horizontalAdvance(line) for line in lines)
        bubble_w = min(rect.width() - 12, text_w + 24)
        bubble_h = line_h * len(lines) + 14
        bubble_x = int((rect.width() - bubble_w) / 2)
        bubble_y = 3

        painter.setPen(QPen(QColor("#242424"), 2))
        painter.setBrush(QColor(255, 255, 255, 238))
        painter.drawRect(QRectF(bubble_x, bubble_y, bubble_w, bubble_h))
        painter.setPen(QColor("#222222"))
        painter.drawText(
            QRect(bubble_x + 10, bubble_y + 5, bubble_w - 20, bubble_h - 8),
            Qt.AlignCenter | Qt.TextWordWrap,
            self.bubble_text,
        )

    def wrap_text(self, metrics, text, max_width):
        lines = []
        current = ""
        for char in text:
            candidate = current + char
            if current and metrics.horizontalAdvance(candidate) > max_width:
                lines.append(current)
                current = char
            else:
                current = candidate
        if current:
            lines.append(current)
        return lines[:5] or [""]


def main():
    if "--say" in sys.argv or "--event" in sys.argv:
        text_parts = []
        mood = None
        duration = None
        event = None
        index = 1
        while index < len(sys.argv):
            arg = sys.argv[index]
            if arg == "--say":
                index += 1
                continue
            if arg == "--event" and index + 1 < len(sys.argv):
                event = sys.argv[index + 1]
                index += 2
                continue
            if arg == "--mood" and index + 1 < len(sys.argv):
                mood = sys.argv[index + 1]
                index += 2
                continue
            if arg == "--duration" and index + 1 < len(sys.argv):
                try:
                    duration = int(sys.argv[index + 1])
                except ValueError:
                    duration = None
                index += 2
                continue
            text_parts.append(arg)
            index += 1
        text = " ".join(text_parts).strip()
        if not text and not event:
            print(
                "Usage: deskpet.py --say \"message\" [--mood happy] [--duration 5600]\n"
                "   or: deskpet.py --event thinking|working|done|waiting|error [message]"
            )
            return
        message = write_pet_message(text, mood=mood, duration=duration, event=event)
        print(f"message sent: [{message['event']}] {message['text']}")
        return

    QApplication.setAttribute(Qt.AA_EnableHighDpiScaling, True)
    QApplication.setAttribute(Qt.AA_UseHighDpiPixmaps, True)
    app = QApplication(sys.argv)
    app.setQuitOnLastWindowClosed(True)
    pet = DeskPet()
    pet.show()
    sys.exit(app.exec_())


if __name__ == "__main__":
    main()
