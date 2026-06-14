from PySide6.QtCore import Qt, Signal
from PySide6.QtWidgets import (
    QInputDialog, QMenu, QMessageBox, QPushButton, QTreeWidget,
    QTreeWidgetItem, QVBoxLayout, QWidget,
)

from figure_archive.db import franchises as franchise_db
from figure_archive.db import lines as line_db
from figure_archive.db import waves as wave_db
from figure_archive.ui.dialogs.franchise_dialog import FranchiseDialog
from figure_archive.ui.dialogs.line_dialog import LineDialog

_ROLE_ID = Qt.UserRole
_ROLE_KIND = Qt.UserRole + 1  # "franchise" | "line" | "group"
_ROLE_PARENT_ID = Qt.UserRole + 2  # immediate parent node id
_ROLE_LINE_ID = Qt.UserRole + 3    # owning line id (for group nodes)


class Sidebar(QWidget):
    line_selected = Signal(str)   # emits line_id
    groups_changed = Signal(str)  # emits line_id whose group structure changed

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
                self._add_group_nodes(l_item, line["id"])
            self._tree.addTopLevelItem(f_item)
        self._restore_expanded(expanded)

    def _add_group_nodes(self, line_item: QTreeWidgetItem, line_id: str) -> None:
        """Build nested group nodes under a line from the group tree."""
        groups = wave_db.list_groups_tree(line_id)
        # Map group id → its tree item so children can attach to parents
        node_by_id: dict[str, QTreeWidgetItem] = {}
        for g in groups:
            label = g["name"] + (f"  {g['year']}" if g.get("year") else "")
            g_item = QTreeWidgetItem([label])
            g_item.setData(0, _ROLE_ID, g["id"])
            g_item.setData(0, _ROLE_KIND, "group")
            g_item.setData(0, _ROLE_PARENT_ID, g.get("parent_id") or line_id)
            g_item.setData(0, _ROLE_LINE_ID, line_id)
            parent_id = g.get("parent_id")
            parent_item = node_by_id.get(parent_id) if parent_id else line_item
            (parent_item or line_item).addChild(g_item)
            node_by_id[g["id"]] = g_item

    def _expanded_ids(self) -> set:
        ids = set()

        def walk(item: QTreeWidgetItem) -> None:
            if item.isExpanded():
                ids.add(item.data(0, _ROLE_ID))
            for i in range(item.childCount()):
                walk(item.child(i))

        for i in range(self._tree.topLevelItemCount()):
            walk(self._tree.topLevelItem(i))
        return ids

    def _restore_expanded(self, expanded: set) -> None:
        def walk(item: QTreeWidgetItem) -> None:
            if item.data(0, _ROLE_ID) in expanded:
                item.setExpanded(True)
            for i in range(item.childCount()):
                walk(item.child(i))

        for i in range(self._tree.topLevelItemCount()):
            walk(self._tree.topLevelItem(i))

    # ── Slots ────────────────────────────────────────────────────────────────

    def _on_item_clicked(self, item: QTreeWidgetItem, _col: int) -> None:
        kind = item.data(0, _ROLE_KIND)
        if kind == "line":
            self.line_selected.emit(item.data(0, _ROLE_ID))
        elif kind == "group":
            # Selecting a group loads its owning line's checklist
            self.line_selected.emit(item.data(0, _ROLE_LINE_ID))

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
            menu.addAction("Add Group", lambda: self._new_group(item))
            menu.addSeparator()
            menu.addAction("Rename", lambda: self._rename_line(item))
            menu.addAction("Delete", lambda: self._delete_line(item))
        elif kind == "group":
            menu.addAction("Add Subgroup", lambda: self._new_subgroup(item))
            menu.addAction("Move to…", lambda: self._move_group(item))
            menu.addSeparator()
            menu.addAction("Rename", lambda: self._rename_group(item))
            menu.addAction("Delete", lambda: self._delete_group(item))
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

    def _expand_id(self, node_id: str) -> None:
        """Expand the node with the given id (any depth)."""
        def walk(item: QTreeWidgetItem) -> bool:
            if item.data(0, _ROLE_ID) == node_id:
                p = item
                while p is not None:
                    p.setExpanded(True)
                    p = p.parent()
                return True
            for i in range(item.childCount()):
                if walk(item.child(i)):
                    return True
            return False

        for i in range(self._tree.topLevelItemCount()):
            if walk(self._tree.topLevelItem(i)):
                return

    # ── Group actions ────────────────────────────────────────────────────────

    def _new_group(self, line_item: QTreeWidgetItem) -> None:
        line_id = line_item.data(0, _ROLE_ID)
        name, ok = QInputDialog.getText(self, "New Group", "Group name:")
        if ok and name.strip():
            wave_db.create_wave(line_id, name.strip())
            self.load_tree()
            self._expand_id(line_id)
            self.groups_changed.emit(line_id)

    def _new_subgroup(self, group_item: QTreeWidgetItem) -> None:
        line_id = group_item.data(0, _ROLE_LINE_ID)
        parent_id = group_item.data(0, _ROLE_ID)
        name, ok = QInputDialog.getText(self, "New Subgroup", "Subgroup name:")
        if ok and name.strip():
            wave_db.create_wave(line_id, name.strip(), parent_id=parent_id)
            self.load_tree()
            self._expand_id(parent_id)
            self.groups_changed.emit(line_id)

    def _rename_group(self, item: QTreeWidgetItem) -> None:
        current = wave_db.get_wave(item.data(0, _ROLE_ID))
        start = current["name"] if current else item.text(0)
        name, ok = QInputDialog.getText(
            self, "Rename Group", "Group name:", text=start
        )
        if ok and name.strip():
            wave_db.rename_wave(item.data(0, _ROLE_ID), name.strip())
            self.load_tree()
            self._expand_id(item.data(0, _ROLE_ID))
            self.groups_changed.emit(item.data(0, _ROLE_LINE_ID))

    def _delete_group(self, item: QTreeWidgetItem) -> None:
        name = item.text(0)
        reply = QMessageBox.question(
            self, "Delete Group",
            f'Delete group "{name}"? Items in it become ungrouped and any '
            f"subgroups move up a level. Items themselves are not deleted.",
            QMessageBox.Yes | QMessageBox.Cancel,
        )
        if reply == QMessageBox.Yes:
            line_id = item.data(0, _ROLE_LINE_ID)
            wave_db.delete_wave(item.data(0, _ROLE_ID))
            self.load_tree()
            self._expand_id(line_id)
            self.groups_changed.emit(line_id)

    def _move_group(self, item: QTreeWidgetItem) -> None:
        line_id = item.data(0, _ROLE_LINE_ID)
        gid = item.data(0, _ROLE_ID)
        blocked = wave_db.descendant_ids(gid) | {gid}

        # Build target choices: top level + every other group in the line
        targets = [("(Top level — no parent)", None)]
        for g in wave_db.list_groups_tree(line_id):
            if g["id"] in blocked:
                continue
            indent = "    " * g["depth"]
            targets.append((f"{indent}{g['name']}", g["id"]))

        labels = [t[0] for t in targets]
        choice, ok = QInputDialog.getItem(
            self, "Move Group", "Move under:", labels, editable=False
        )
        if not ok:
            return
        parent_id = targets[labels.index(choice)][1]
        try:
            wave_db.set_parent(gid, parent_id)
        except ValueError as exc:
            QMessageBox.warning(self, "Cannot Move", str(exc))
            return
        self.load_tree()
        self._expand_id(gid)
        self.groups_changed.emit(line_id)
