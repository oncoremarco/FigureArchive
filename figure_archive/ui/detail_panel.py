from pathlib import Path

from PySide6.QtCore import Qt, QTimer, Signal
from PySide6.QtGui import QPixmap
from PySide6.QtWidgets import (
    QCheckBox, QComboBox, QDoubleSpinBox, QFileDialog, QFormLayout, QFrame,
    QHBoxLayout, QLabel, QLineEdit, QMenu, QPlainTextEdit, QPushButton,
    QScrollArea, QVBoxLayout, QWidget,
)

from figure_archive.core import image_cache
from figure_archive.db import items as item_db
from figure_archive.db import item_images as img_db
from figure_archive.db import personal_photos as photo_db
from figure_archive.db import collection_entries as ce
from figure_archive.db import tags as tag_db
from figure_archive.plugins import loader
from figure_archive.ui.image_carousel import ImageCarousel
from figure_archive.ui.widgets.star_rating import StarRating
from figure_archive.ui.dialogs.tag_dialog import TagDialog

_IMG_ACCEPT = "Images (*.jpg *.jpeg *.png *.gif *.webp);;All files (*)"

_STATUS_OPTIONS = [
    (ce.NOT_OWNED, "Not Owned"),
    (ce.OWNED, "Owned"),
    (ce.WANTED, "Wanted"),
    (ce.ON_ORDER, "On Order"),
    (ce.SOLD, "Sold / Traded"),
]

_PRIORITY_OPTIONS = [
    (ce.WATCHING, "Watching"),
    (ce.WISH_WANTED, "Wanted"),
    (ce.GRAIL, "Grail"),
]

_SAVE_DEBOUNCE_MS = 1500


class DetailPanel(QWidget):
    """Item detail + personal data editor with debounced auto-save."""
    closed = Signal()
    data_saved = Signal()  # emitted after a save so the checklist can refresh

    def __init__(self):
        super().__init__()
        self._item_id: str | None = None
        self._loading = False
        self.setMinimumWidth(340)

        self._save_timer = QTimer(self)
        self._save_timer.setSingleShot(True)
        self._save_timer.setInterval(_SAVE_DEBOUNCE_MS)
        self._save_timer.timeout.connect(self._save)

        self._build_ui()

    # ── UI construction ──────────────────────────────────────────────────────

    def _build_ui(self) -> None:
        outer = QVBoxLayout(self)
        outer.setContentsMargins(0, 0, 0, 0)
        outer.setSpacing(0)

        # Top bar: close + title + favorite/grail quick toggles
        topbar = QWidget()
        topbar.setStyleSheet("background-color: #181825;")
        tl = QHBoxLayout(topbar)
        tl.setContentsMargins(12, 10, 12, 10)
        close_btn = QPushButton("✕")
        close_btn.setFixedWidth(30)
        close_btn.clicked.connect(self._on_close)
        tl.addWidget(close_btn)
        self._title = QLabel("")
        self._title.setStyleSheet("font-size: 15px; font-weight: bold;")
        tl.addWidget(self._title, 1)
        self._fav_btn = QPushButton("☆")
        self._fav_btn.setFixedWidth(34)
        self._fav_btn.setCheckable(True)
        self._fav_btn.clicked.connect(self._on_fav_clicked)
        tl.addWidget(self._fav_btn)
        outer.addWidget(topbar)

        self._breadcrumb = QLabel("")
        self._breadcrumb.setStyleSheet("color: #6c7086; font-size: 11px; padding: 4px 12px;")
        outer.addWidget(self._breadcrumb)

        # Scrollable body
        scroll = QScrollArea()
        scroll.setWidgetResizable(True)
        scroll.setFrameShape(QFrame.Shape.NoFrame)
        body = QWidget()
        self._body = QVBoxLayout(body)
        self._body.setContentsMargins(14, 8, 14, 14)
        self._body.setSpacing(12)
        scroll.setWidget(body)
        outer.addWidget(scroll, 1)

        self._build_catalog_section()
        self._build_personal_section()
        self._build_photos_section()
        self._build_tags_section()
        self._body.addStretch(1)

        # Save indicator
        self._save_label = QLabel("")
        self._save_label.setStyleSheet("color: #a6e3a1; font-size: 11px; padding: 4px 12px;")
        outer.addWidget(self._save_label)

    def _section_header(self, text: str) -> QLabel:
        lbl = QLabel(text)
        lbl.setStyleSheet(
            "font-weight: bold; color: #89b4fa; font-size: 11px;"
            "border-bottom: 1px solid #313244; padding-bottom: 3px;"
        )
        return lbl

    def _build_catalog_section(self) -> None:
        # Primary image preview
        self._image = QLabel("No Image")
        self._image.setFixedHeight(160)
        self._image.setAlignment(Qt.AlignCenter)
        self._image.setStyleSheet(
            "background-color: #181825; border: 1px solid #313244;"
            "border-radius: 6px; color: #45475a;"
        )
        self._body.addWidget(self._image)

        # Image action buttons
        img_btns = QHBoxLayout()
        set_img_btn = QPushButton("Set Image…")
        set_img_btn.clicked.connect(self._set_primary_image)
        img_btns.addWidget(set_img_btn)
        img_btns.addStretch(1)
        self._body.addLayout(img_btns)

        # Additional catalog images carousel
        self._body.addWidget(self._section_header("CATALOG IMAGES"))
        self._catalog_carousel = ImageCarousel(can_add=True)
        self._catalog_carousel.image_selected.connect(self._preview_image)
        self._catalog_carousel.image_added.connect(self._add_catalog_image)
        self._catalog_carousel.image_removed.connect(self._remove_catalog_image)
        self._body.addWidget(self._catalog_carousel)

        self._catalog_info = QLabel("")
        self._catalog_info.setWordWrap(True)
        self._catalog_info.setStyleSheet("color: #cdd6f4; font-size: 12px;")
        self._body.addWidget(self._catalog_info)

    def _build_personal_section(self) -> None:
        self._body.addWidget(self._section_header("YOUR COLLECTION"))
        form = QFormLayout()
        form.setSpacing(8)
        form.setLabelAlignment(Qt.AlignRight)

        self._status = QComboBox()
        for val, label in _STATUS_OPTIONS:
            self._status.addItem(label, userData=val)
        self._status.currentIndexChanged.connect(self._on_status_changed)
        form.addRow("Status:", self._status)

        self._priority = QComboBox()
        for val, label in _PRIORITY_OPTIONS:
            self._priority.addItem(label, userData=val)
        self._priority.currentIndexChanged.connect(self._schedule_save)
        self._priority_row = self._priority
        form.addRow("Priority:", self._priority)

        self._condition = QComboBox()
        self._condition.currentIndexChanged.connect(self._schedule_save)
        form.addRow("Condition:", self._condition)

        self._box_condition = QComboBox()
        self._box_condition.currentIndexChanged.connect(self._schedule_save)
        self._box_condition_label = "Box Cond.:"
        form.addRow("Box Cond.:", self._box_condition)

        self._packaging = QComboBox()
        self._packaging.currentIndexChanged.connect(self._schedule_save)
        form.addRow("Packaging:", self._packaging)

        self._complete = QCheckBox("Complete")
        self._complete.stateChanged.connect(self._schedule_save)
        form.addRow("", self._complete)

        self._missing = QLineEdit()
        self._missing.setPlaceholderText("Missing accessories…")
        self._missing.textChanged.connect(self._schedule_save)
        form.addRow("Missing:", self._missing)

        # Flags row
        flags = QHBoxLayout()
        self._display = QCheckBox("On Display")
        self._repair = QCheckBox("Needs Repair")
        self._sealed = QCheckBox("Sealed")
        for cb in (self._display, self._repair, self._sealed):
            cb.stateChanged.connect(self._schedule_save)
            flags.addWidget(cb)
        flags.addStretch(1)
        flags_w = QWidget()
        flags_w.setLayout(flags)
        form.addRow("Flags:", flags_w)

        # Loaned
        loan_row = QHBoxLayout()
        self._loaned = QCheckBox("Loaned to")
        self._loaned.stateChanged.connect(self._on_loaned_changed)
        self._loaned_to = QLineEdit()
        self._loaned_to.setPlaceholderText("name")
        self._loaned_to.textChanged.connect(self._schedule_save)
        loan_row.addWidget(self._loaned)
        loan_row.addWidget(self._loaned_to)
        loan_w = QWidget()
        loan_w.setLayout(loan_row)
        form.addRow("", loan_w)

        self._for_sale = QCheckBox("Listed for sale")
        self._for_sale.stateChanged.connect(self._schedule_save)
        form.addRow("", self._for_sale)

        self._acquired_from = QLineEdit()
        self._acquired_from.textChanged.connect(self._schedule_save)
        form.addRow("Acquired from:", self._acquired_from)

        self._paid = QDoubleSpinBox()
        self._paid.setRange(0, 1_000_000)
        self._paid.setPrefix("$ ")
        self._paid.valueChanged.connect(self._schedule_save)
        form.addRow("Paid:", self._paid)

        self._value = QDoubleSpinBox()
        self._value.setRange(0, 1_000_000)
        self._value.setPrefix("$ ")
        self._value.valueChanged.connect(self._schedule_save)
        form.addRow("Est. value:", self._value)

        self._rating = StarRating()
        self._rating.changed.connect(self._schedule_save)
        form.addRow("Rating:", self._rating)

        self._body.addLayout(form)

        self._notes = QPlainTextEdit()
        self._notes.setPlaceholderText("Personal notes…")
        self._notes.setFixedHeight(80)
        self._notes.textChanged.connect(self._schedule_save)
        self._body.addWidget(QLabel("Notes:"))
        self._body.addWidget(self._notes)

    def _build_photos_section(self) -> None:
        self._body.addWidget(self._section_header("YOUR PHOTOS"))
        self._photos_carousel = ImageCarousel(can_add=True)
        self._photos_carousel.image_selected.connect(self._preview_image)
        self._photos_carousel.image_added.connect(self._add_personal_photo)
        self._photos_carousel.image_removed.connect(self._remove_personal_photo)
        self._body.addWidget(self._photos_carousel)

    def _build_tags_section(self) -> None:
        self._body.addWidget(self._section_header("TAGS"))
        self._tags_container = QWidget()
        self._tags_layout = QHBoxLayout(self._tags_container)
        self._tags_layout.setContentsMargins(0, 0, 0, 0)
        self._tags_layout.setSpacing(6)
        self._body.addWidget(self._tags_container)

    # ── Loading an item ──────────────────────────────────────────────────────

    def load_item(self, item_id: str) -> None:
        self._flush_pending_save()
        self._item_id = item_id
        item = item_db.get_item(item_id)
        if not item:
            return
        entry = ce.get_or_create_entry(item_id)
        line = self._lookup_line(item["line_id"])
        type_plugin = loader.get_type_plugin(line.get("type_plugin_id") if line else None)

        self._loading = True

        self._title.setText(item["name"])
        self._breadcrumb.setText(self._build_breadcrumb(line, item))
        self._fav_btn.setChecked(bool(entry.get("is_favorite")))
        self._render_fav_button()

        # Images
        self._load_primary_image(item.get("primary_image"))
        self._catalog_carousel.set_images(
            [r["local_path"] for r in img_db.list_images(item_id) if r.get("local_path")]
        )
        self._photos_carousel.set_images(
            [r["local_path"] for r in photo_db.list_photos(item_id) if r.get("local_path")]
        )

        # Catalog info
        self._catalog_info.setText(self._format_catalog(item))

        # Condition vocabularies from the type plugin
        self._populate_condition_combos(type_plugin)

        # Status
        self._set_combo_value(self._status, entry.get("owned") or 0)
        self._set_combo_value(self._priority, entry.get("wishlist_priority") or 0)
        self._set_combo_text(self._condition, entry.get("condition"))
        self._set_combo_text(self._box_condition, entry.get("box_condition"))
        self._set_combo_text(self._packaging, entry.get("packaging_state"))

        self._complete.setChecked(bool(entry.get("is_complete", 1)))
        self._missing.setText(entry.get("missing_accessories") or "")
        self._display.setChecked(bool(entry.get("on_display")))
        self._repair.setChecked(bool(entry.get("needs_repair")))
        self._sealed.setChecked(bool(entry.get("is_sealed")))
        self._loaned.setChecked(bool(entry.get("is_loaned")))
        self._loaned_to.setText(entry.get("loaned_to") or "")
        self._loaned_to.setVisible(bool(entry.get("is_loaned")))
        self._for_sale.setChecked(bool(entry.get("is_for_sale")))
        self._acquired_from.setText(entry.get("acquired_from") or "")
        self._paid.setValue(entry.get("paid_price") or 0)
        self._value.setValue(entry.get("estimated_value") or 0)
        self._rating.set_value(entry.get("personal_rating") or 0)
        self._notes.setPlainText(entry.get("personal_notes") or "")

        self._update_priority_visibility()
        self._refresh_tags()

        self._loading = False

    # ── Image handling ───────────────────────────────────────────────────────

    def _load_primary_image(self, local_path: str | None) -> None:
        if not local_path:
            self._image.setText("No Image")
            self._image.setPixmap(QPixmap())
            return
        thumb = image_cache.get_thumbnail_path(local_path)
        if thumb and thumb.exists():
            px = QPixmap(str(thumb)).scaled(
                self._image.width() or 300, 160,
                Qt.KeepAspectRatio, Qt.SmoothTransformation,
            )
            self._image.setText("")
            self._image.setPixmap(px)
        else:
            self._image.setText("No Image")

    def _preview_image(self, local_path: str) -> None:
        """Show a carousel-selected image in the primary preview area."""
        self._load_primary_image(local_path)

    def _set_primary_image(self) -> None:
        if not self._item_id:
            return
        path, _ = QFileDialog.getOpenFileName(self, "Select image", "", _IMG_ACCEPT)
        if not path:
            return
        dest = image_cache.cache_image_from_file(path, self._item_id)
        if dest:
            img_db.set_primary_image(self._item_id, str(dest))
            img_db.add_image(self._item_id, str(dest))
            self._load_primary_image(str(dest))
            self._catalog_carousel.set_images(
                [r["local_path"] for r in img_db.list_images(self._item_id)
                 if r.get("local_path")]
            )
            self.data_saved.emit()

    def _add_catalog_image(self, path: str) -> None:
        if not self._item_id:
            return
        dest = image_cache.cache_image_from_file(path, self._item_id)
        if dest:
            img_db.add_image(self._item_id, str(dest))
            self._catalog_carousel.set_images(
                [r["local_path"] for r in img_db.list_images(self._item_id)
                 if r.get("local_path")]
            )
            if not item_db.get_item(self._item_id).get("primary_image"):
                img_db.set_primary_image(self._item_id, str(dest))
                self._load_primary_image(str(dest))
            self.data_saved.emit()

    def _remove_catalog_image(self, path: str) -> None:
        if not self._item_id:
            return
        rows = img_db.list_images(self._item_id)
        for row in rows:
            if row["local_path"] == path:
                img_db.remove_image(row["id"])
        item = item_db.get_item(self._item_id)
        if item and item.get("primary_image") == path:
            remaining = [r for r in img_db.list_images(self._item_id) if r.get("local_path")]
            new_primary = remaining[0]["local_path"] if remaining else None
            img_db.set_primary_image(self._item_id, new_primary)
            self._load_primary_image(new_primary)
        self._catalog_carousel.set_images(
            [r["local_path"] for r in img_db.list_images(self._item_id)
             if r.get("local_path")]
        )
        self.data_saved.emit()

    def _add_personal_photo(self, path: str) -> None:
        if not self._item_id:
            return
        dest = image_cache.cache_image_from_file(path, self._item_id)
        if dest:
            photo_db.add_photo(self._item_id, str(dest))
            self._photos_carousel.set_images(
                [r["local_path"] for r in photo_db.list_photos(self._item_id)
                 if r.get("local_path")]
            )

    def _remove_personal_photo(self, path: str) -> None:
        if not self._item_id:
            return
        for row in photo_db.list_photos(self._item_id):
            if row["local_path"] == path:
                photo_db.remove_photo(row["id"])
        self._photos_carousel.set_images(
            [r["local_path"] for r in photo_db.list_photos(self._item_id)
             if r.get("local_path")]
        )

    def _lookup_line(self, line_id: str) -> dict | None:
        from figure_archive.db.connection import get_connection
        row = get_connection().execute(
            "SELECT l.*, f.name AS franchise_name FROM lines l "
            "JOIN franchises f ON f.id = l.franchise_id WHERE l.id=?",
            (line_id,),
        ).fetchone()
        return dict(row) if row else None

    def _build_breadcrumb(self, line: dict | None, item: dict) -> str:
        if not line:
            return ""
        parts = [line.get("franchise_name", ""), line.get("name", "")]
        return "  ›  ".join(p for p in parts if p)

    def _format_catalog(self, item: dict) -> str:
        bits = []
        if item.get("year"):
            bits.append(f"<b>Year:</b> {item['year']}")
        bits.append(f"<b>Type:</b> {item.get('item_type', '').capitalize()}")
        if item.get("manufacturer"):
            bits.append(f"<b>Mfr:</b> {item['manufacturer']}")
        if item.get("scale"):
            bits.append(f"<b>Scale:</b> {item['scale']}")
        if item.get("upc"):
            bits.append(f"<b>UPC:</b> {item['upc']}")
        line1 = "   ".join(bits)
        extra = ""
        if item.get("accessories"):
            extra += f"<br><b>Accessories:</b> {item['accessories']}"
        if item.get("description"):
            extra += f"<br><br>{item['description']}"
        return line1 + extra

    def _populate_condition_combos(self, type_plugin) -> None:
        vocab = list(type_plugin.condition_vocabulary) if type_plugin else []
        packaging = list(type_plugin.packaging_states) if type_plugin else []
        for combo, opts in (
            (self._condition, vocab),
            (self._box_condition, vocab),
            (self._packaging, packaging),
        ):
            combo.blockSignals(True)
            combo.clear()
            combo.addItem("—", userData=None)
            for o in opts:
                combo.addItem(o, userData=o)
            combo.blockSignals(True)
            combo.blockSignals(False)

    # ── Save ─────────────────────────────────────────────────────────────────

    def _schedule_save(self, *args) -> None:
        if self._loading or not self._item_id:
            return
        self._save_timer.start()

    def _flush_pending_save(self) -> None:
        if self._save_timer.isActive():
            self._save_timer.stop()
            self._save()

    def _save(self) -> None:
        if not self._item_id:
            return
        ce.update_entry(
            self._item_id,
            owned=self._status.currentData(),
            wishlist_priority=self._priority.currentData(),
            condition=self._condition.currentData(),
            box_condition=self._box_condition.currentData(),
            packaging_state=self._packaging.currentData(),
            is_complete=1 if self._complete.isChecked() else 0,
            missing_accessories=self._missing.text().strip() or None,
            on_display=1 if self._display.isChecked() else 0,
            needs_repair=1 if self._repair.isChecked() else 0,
            is_sealed=1 if self._sealed.isChecked() else 0,
            is_loaned=1 if self._loaned.isChecked() else 0,
            loaned_to=self._loaned_to.text().strip() or None,
            is_for_sale=1 if self._for_sale.isChecked() else 0,
            is_favorite=1 if self._fav_btn.isChecked() else 0,
            acquired_from=self._acquired_from.text().strip() or None,
            paid_price=self._paid.value() or None,
            estimated_value=self._value.value() or None,
            personal_rating=self._rating.value() or None,
            personal_notes=self._notes.toPlainText().strip() or None,
        )
        self._show_saved()
        self.data_saved.emit()

    def _show_saved(self) -> None:
        self._save_label.setText("✓ Saved")
        QTimer.singleShot(2000, lambda: self._save_label.setText(""))

    # ── Small slots ──────────────────────────────────────────────────────────

    def _on_status_changed(self, *_a) -> None:
        self._update_priority_visibility()
        self._schedule_save()

    def _update_priority_visibility(self) -> None:
        status = self._status.currentData()
        show = status in (ce.WANTED, ce.ON_ORDER)
        self._priority.setVisible(show)

    def _on_loaned_changed(self, *_a) -> None:
        self._loaned_to.setVisible(self._loaned.isChecked())
        self._schedule_save()

    def _on_fav_clicked(self) -> None:
        self._render_fav_button()
        self._schedule_save()

    def _render_fav_button(self) -> None:
        if self._fav_btn.isChecked():
            self._fav_btn.setText("★")
            self._fav_btn.setStyleSheet("color: #f9e2af; font-size: 16px;")
        else:
            self._fav_btn.setText("☆")
            self._fav_btn.setStyleSheet("font-size: 16px;")

    def _on_close(self) -> None:
        self._flush_pending_save()
        self.closed.emit()

    # ── Tags ─────────────────────────────────────────────────────────────────

    def _refresh_tags(self) -> None:
        while self._tags_layout.count():
            w = self._tags_layout.takeAt(0).widget()
            if w:
                w.deleteLater()
        if not self._item_id:
            return
        for tag in tag_db.list_tags_for_item(self._item_id):
            self._tags_layout.addWidget(self._make_chip(tag))
        add = QPushButton("＋ add tag")
        add.setStyleSheet(
            "border: 1px dashed #45475a; border-radius: 9px; padding: 1px 8px;"
            "color: #6c7086; font-size: 11px;"
        )
        add.clicked.connect(self._add_tag_menu)
        self._tags_layout.addWidget(add)
        self._tags_layout.addStretch(1)

    def _make_chip(self, tag: dict) -> QPushButton:
        chip = QPushButton(tag["name"])
        color = tag.get("color") or "#89b4fa"
        chip.setStyleSheet(
            f"color: {color}; border: 1px solid {color}; border-radius: 9px;"
            "padding: 1px 8px; font-size: 11px;"
        )
        chip.setToolTip("Click to remove")
        chip.clicked.connect(lambda: self._remove_tag(tag["id"]))
        return chip

    def _add_tag_menu(self) -> None:
        menu = QMenu(self)
        assigned = {t["id"] for t in tag_db.list_tags_for_item(self._item_id)}
        for tag in tag_db.list_tags():
            if tag["id"] not in assigned:
                menu.addAction(tag["name"], lambda t=tag: self._assign_tag(t["id"]))
        if not menu.isEmpty():
            menu.addSeparator()
        menu.addAction("New tag…", self._create_tag)
        menu.exec(self.cursor().pos())

    def _assign_tag(self, tag_id: str) -> None:
        tag_db.add_tag_to_item(self._item_id, tag_id)
        self._refresh_tags()

    def _remove_tag(self, tag_id: str) -> None:
        tag_db.remove_tag_from_item(self._item_id, tag_id)
        self._refresh_tags()

    def _create_tag(self) -> None:
        dlg = TagDialog(self)
        if dlg.exec() == TagDialog.Accepted:
            try:
                tid = tag_db.create_tag(dlg.name(), dlg.color())
                tag_db.add_tag_to_item(self._item_id, tid)
            except Exception:
                pass  # duplicate name
            self._refresh_tags()

    # ── Helpers ──────────────────────────────────────────────────────────────

    def _set_combo_value(self, combo: QComboBox, value) -> None:
        idx = combo.findData(value)
        combo.setCurrentIndex(idx if idx >= 0 else 0)

    def _set_combo_text(self, combo: QComboBox, value) -> None:
        if value is None:
            combo.setCurrentIndex(0)
            return
        idx = combo.findData(value)
        combo.setCurrentIndex(idx if idx >= 0 else 0)
