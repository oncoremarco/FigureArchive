from PySide6.QtCore import Qt, Signal
from PySide6.QtWidgets import (
    QMenu, QMessageBox, QPushButton, QTreeWidget,
    QTreeWidgetItem, QVBoxLayout, QWidget,
)

from figure_archive.db import franchises as franchise_db
from figure_archive.db import lines as line_db
from figure_archive.ui.dialogs.franchise_dialog import FranchiseDialog
from figure_archive.ui.dialogs.line_dialog import LineDialog

_ROLE_ID = Qt.UserRole
_ROLE_KIND = Qt.UserRole + 1  # "franchise" | "line"
_ROLE_PARENT_ID = Qt.UserRole + 2


class Sidebar(QWidget):
    line_selected = Signal(str)  # emits line_id

    def __init__(self, parent=None):
        super().__init__(parent)
        self._build_ui()
        self.load_tree()

    # ── UI construction ──────────────────────────────────────────────────────

    def _build_ui(self) -> None:
        layout = QVBoxLayout(self)
        layout.setContentsMargins(0, 0, 0, 0)
        layout.setSpacing(0)

        self._tree = QTreeWidget()
        self._tree.setHeaderHidden(True)
        self._tree.setAnimated(True)
        self._tree.setIndentation(16)
        self._tree.setContextMenuPolicy(Qt.CustomContextMenu)
        self._tree.customContextMenuRequested.connect(self._on_context_menu)
        self._tree.itemClicked.connect(self._on_item_clicked)
        layout.addWidget(self._tree, 1)

        self._new_franchise_btn = QPushButton("＋  New Franchise")
        self._new_franchise_btn.setStyleSheet(
            "border: none; border-top: 1px solid #313244;"
            "border-radius: 0; padding: 10px; text-align: left; color: #89b4fa;"
        )
        self._new_franchise_btn.clicked.connect(self._new_franchise)
        layout.addWidget(self._new_franchise_btn)

    # ── Tree population ──────────────────────────────────────────────────────

    def load_tree(self) -> None:
        expanded = self._expanded_ids()
        self._tree.clear()
        for f in franchise_db.list_franchises():
            f_item = QTreeWidgetItem([f["name"]])
            f_item.setData(0, _ROLE_ID, f["id"])
            f_item.setData(0, _ROLE_KIND, "franchise")
            for line in line_db.list_lines(f["id"]):
                l_item = QTreeWidgetItem([line["name"]])
                l_item.setData(0, _ROLE_ID, line["id"])
                l_item.setData(0, _ROLE_KIND, "line")
                l_item.setData(0, _ROLE_PARENT_ID, f["id"])
                f_item.addChild(l_item)
            self._tree.addTopLevelItem(f_item)
            if f["id"] in expanded:
                f_item.setExpanded(True)

    def _expanded_ids(self) -> set:
        ids = set()
        for i in range(self._tree.topLevelItemCount()):
            item = self._tree.topLevelItem(i)
            if item.isExpanded():
                ids.add(item.data(0, _ROLE_ID))
        return ids

    # ── Slots ────────────────────────────────────────────────────────────────

    def _on_item_clicked(self, item: QTreeWidgetItem, _col: int) -> None:
        if item.data(0, _ROLE_KIND) == "line":
            self.line_selected.emit(item.data(0, _ROLE_ID))

    def _on_context_menu(self, pos) -> None:
        item = self._tree.itemAt(pos)
        if item is None:
            return
        kind = item.data(0, _ROLE_KIND)
        menu = QMenu(self)
        if kind == "franchise":
            menu.addAction("Add Line", lambda: self._new_line(item))
            menu.addSeparator()
            menu.addAction("Rename", lambda: self._rename_franchise(item))
            menu.addAction("Delete", lambda: self._delete_franchise(item))
        elif kind == "line":
            menu.addAction("Rename", lambda: self._rename_line(item))
            menu.addAction("Delete", lambda: self._delete_line(item))
        menu.exec(self._tree.viewport().mapToGlobal(pos))

    # ── Franchise actions ────────────────────────────────────────────────────

    def _new_franchise(self) -> None:
        dlg = FranchiseDialog(self)
        if dlg.exec() == FranchiseDialog.Accepted:
            franchise_db.create_franchise(dlg.name())
            self.load_tree()

    def _rename_franchise(self, item: QTreeWidgetItem) -> None:
        dlg = FranchiseDialog(self, existing_name=item.text(0))
        if dlg.exec() == FranchiseDialog.Accepted:
            franchise_db.rename_franchise(item.data(0, _ROLE_ID), dlg.name())
            self.load_tree()

    def _delete_franchise(self, item: QTreeWidgetItem) -> None:
        name = item.text(0)
        reply = QMessageBox.question(
            self, "Delete Franchise",
            f'Delete "{name}" and all its lines? This cannot be undone.',
            QMessageBox.Yes | QMessageBox.Cancel,
        )
        if reply == QMessageBox.Yes:
            franchise_db.delete_franchise(item.data(0, _ROLE_ID))
            self.load_tree()

    # ── Line actions ─────────────────────────────────────────────────────────

    def _new_line(self, franchise_item: QTreeWidgetItem) -> None:
        dlg = LineDialog(self)
        if dlg.exec() == LineDialog.Accepted:
            fid = franchise_item.data(0, _ROLE_ID)
            line_db.create_line(fid, dlg.name(), dlg.type_plugin_id())
            self.load_tree()
            # Re-expand the parent franchise
            self._expand_franchise(fid)

    def _rename_line(self, item: QTreeWidgetItem) -> None:
        dlg = LineDialog(self, existing_name=item.text(0), show_type=False)
        if dlg.exec() == LineDialog.Accepted:
            line_db.rename_line(item.data(0, _ROLE_ID), dlg.name())
            self.load_tree()
            self._expand_franchise(item.data(0, _ROLE_PARENT_ID))

    def _delete_line(self, item: QTreeWidgetItem) -> None:
        name = item.text(0)
        reply = QMessageBox.question(
            self, "Delete Line",
            f'Delete "{name}"? All items in this line will be removed.',
            QMessageBox.Yes | QMessageBox.Cancel,
        )
        if reply == QMessageBox.Yes:
            parent_id = item.data(0, _ROLE_PARENT_ID)
            line_db.delete_line(item.data(0, _ROLE_ID))
            self.load_tree()
            self._expand_franchise(parent_id)

    def _expand_franchise(self, franchise_id: str) -> None:
        for i in range(self._tree.topLevelItemCount()):
            f_item = self._tree.topLevelItem(i)
            if f_item.data(0, _ROLE_ID) == franchise_id:
                f_item.setExpanded(True)
                break
