from PyQt6.QtWidgets import QComboBox, QStyledItemDelegate, QLineEdit
from PyQt6.QtCore import Qt

class CheckableComboBox(QComboBox):
    def __init__(self, parent=None):
        super().__init__(parent)
        self._line_edit = QLineEdit(self)
        self._line_edit.setReadOnly(True)
        self.setLineEdit(self._line_edit)
        
        self.view().pressed.connect(self.handle_item_pressed)
        self.setItemDelegate(QStyledItemDelegate(self))
        self.model().dataChanged.connect(self._on_data_changed)
        self._changed = False
        self._updating = False

    def handle_item_pressed(self, index):
        item = self.model().itemFromIndex(index)
        # Manually toggle state to allow clicking the text area, not just the checkbox itself
        new_state = Qt.CheckState.Unchecked if item.checkState() == Qt.CheckState.Checked else Qt.CheckState.Checked
        item.setCheckState(new_state)

    def _on_data_changed(self, topLeft, bottomRight, roles):
        if self._updating:
            return
            
        self._updating = True
        index = topLeft
        item = self.model().itemFromIndex(index)
        
        if index.row() == 0:
            new_state = item.checkState()
            self.model().blockSignals(True)
            for i in range(1, self.count()):
                self.model().item(i, 0).setCheckState(new_state)
            self.model().blockSignals(False)
            # Emit dataChanged for the whole range once
            if self.count() > 1:
                self.model().dataChanged.emit(self.model().index(1, 0), self.model().index(self.count() - 1, 0), [Qt.ItemDataRole.CheckStateRole])
        else:
            all_checked = all(self.model().item(i, 0).checkState() == Qt.CheckState.Checked for i in range(1, self.count()))
            self.model().blockSignals(True)
            self.model().item(0, 0).setCheckState(Qt.CheckState.Checked if all_checked else Qt.CheckState.Unchecked)
            self.model().blockSignals(False)
            self.model().dataChanged.emit(self.model().index(0, 0), self.model().index(0, 0), [Qt.ItemDataRole.CheckStateRole])
            
        self._changed = True
        self.update_text()
        self._updating = False

    def hidePopup(self):
        if not self._changed:
            super().hidePopup()
        self._changed = False

    def addItems(self, texts: list[str]):
        for text in texts:
            self.addItem(text)
            item = self.model().item(self.count() - 1, 0)
            item.setFlags(Qt.ItemFlag.ItemIsEnabled)
            item.setCheckState(Qt.CheckState.Checked)
        self.update_text()

    def get_checked_items(self) -> list[str]:
        checked = []
        for i in range(1, self.count()):
            item = self.model().item(i, 0)
            if item.checkState() == Qt.CheckState.Checked:
                checked.append(item.text())
        return checked

    def update_text(self, *args):
        checked = self.get_checked_items()
        if not checked:
            self._line_edit.setText("None")
        elif len(checked) == self.count() - 1:
            self._line_edit.setText(self.model().item(0, 0).text())
        else:
            self._line_edit.setText(", ".join(checked))
