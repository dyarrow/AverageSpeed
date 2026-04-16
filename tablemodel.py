from PyQt5.QtCore import Qt, QAbstractTableModel, QModelIndex, Qt, QSortFilterProxyModel, QAbstractTableModel, QRegExp,QAbstractItemModel
from PyQt5 import  QtCore
from PyQt5.QtGui import QStandardItemModel, QStandardItem,QBrush,QColor
import os
from copy import deepcopy

class CustomTableModel(QAbstractTableModel):
    def __init__(self, data, headers, parent=None):
        QAbstractItemModel.__init__(self, parent)
        #super().__init__()
        self._data = data
        self.horizontalHeaders = [''] * len(headers)

        self.colors = dict()

        row=0
        for item in headers:
            self.setHeaderData(row, Qt.Horizontal, item)
            row+=1
        
        #self._data = data
    
    def insertRows(self, new_row, position, rows, parent=QModelIndex()):
        try:
            position = (position + self.newRowCount()) if position < 0 else position
            start = position
            end = position + rows - 1

            #if end <= 8:
            self.beginResetModel()
            self.beginInsertRows(parent, start, end)
            self._data.append(new_row) 
            self.endInsertRows()
            self.endResetModel()
            return True
        except Exception as e:
            print(e)
        #else:
        #    self.beginInsertRows(parent, start, end)
        #    self._data.append(new_row) 
        #    self.endInsertRows()
        #    self.removeRows(0, 0)
        #    return True
    
    def setData(self, index, value, role):
        if role == Qt.EditRole:
            # Set the value into the frame.
            self._data[index.row()][index.column()] = value
            return True

        return False

    def setHeaderData(self, section, orientation, data, role=Qt.EditRole):
        if orientation == Qt.Horizontal and role in (Qt.DisplayRole, Qt.EditRole):
            try:
                self.horizontalHeaders[section] = data
                return True
            except:
                return False
        return super().setHeaderData(section, orientation, data, role)
    
    def headerData(self, section, orientation, role=Qt.DisplayRole):
        if orientation == Qt.Horizontal and role == Qt.DisplayRole:
            try:
                return self.horizontalHeaders[section]
            except:
                pass
        return super().headerData(section, orientation, role)

    def data(self, index, role=Qt.DisplayRole):
        if index.isValid():
            if role == Qt.DisplayRole:
                return self._data[index.row()][index.column()]
            if role == Qt.EditRole:
                return self._data[index.row()][index.column()]
            if role == Qt.BackgroundRole:
                color = self.colors.get((index.row(), index.column()))
                if color is not None:
                    return color
        return None
    
    def newRowCount(self, index=QModelIndex()):                     # +
        return  0 if index.isValid() else len(self._data) 

    def rowCount(self, index):
        return len(self._data)

    def columnCount(self, index):
        return len(self.horizontalHeaders)

    def change_color(self, row, column, color):
        ix = self.index(row, column)
        self.colors[(row, column)] = color
        self.dataChanged.emit(ix, ix, (Qt.BackgroundRole,))

    def flags(self, index):
        flags = super(self.__class__, self).flags(index)
        flags |= Qt.ItemIsEditable
        flags |= Qt.ItemIsSelectable
        flags |= Qt.ItemIsEnabled
        flags |= Qt.ItemIsDragEnabled
        flags |= Qt.ItemIsDropEnabled
        return flags

    def search(self,searchString):
        for item in self._data:
            if str(item[0]) == str(searchString):
                return item
        return None
    
class CustomProxyModel(QSortFilterProxyModel):
    def __init__(self, parent=None):
        super().__init__(parent)
        self._filters = dict()
        self.showDiffsOnly=False

    @property
    def filters(self):
        return self._filters
    
    @QtCore.pyqtSlot(bool)
    def showDiffsSlot(self,toggleState):
        print(f'Setting the filter to only show different values {toggleState}')
        self.showDiffsOnly=toggleState
        self.invalidateFilter()
        

    def filterAcceptsRow(self, source_row: int, source_parent: QModelIndex) -> bool:
        diffIdx = self.sourceModel().index(source_row, 3, source_parent) #The model holds a list of differences in col 4
        if self.showDiffsOnly:
            return (super().filterAcceptsRow(source_row, source_parent) and (self.sourceModel().data(diffIdx)))
        else:
            return super().filterAcceptsRow(source_row, source_parent) 
    
    def filterAcceptsColumn(self, source_column: int, source_parent: QModelIndex) -> bool:
        """ if source_column<=2:
            # Columns 0,1 & 2 are all we want to show, column 3 identifies if the values are different
            return True
        return False """
        return True
    
class CustomTreeModel(QStandardItemModel):
    def __init__(self, header, data, compare_configurations, comparison_data=None):
        super(CustomTreeModel, self).__init__(0, len(header))
        self.setHorizontalHeaderLabels(header)

        self._local_data=deepcopy(data)
        self._comparison_data=deepcopy(comparison_data)

        #If flag is set to True then do comparison
        self.compare_configurations=compare_configurations
        
        self.setup_model_data()

    def setup_model_data(self):
        #If default comparison is turned on then compare to comparison config and update local dictionary for display
        if self.compare_configurations and self._comparison_data is not None and self._comparison_data != "":
            self.do_comparison()
        
        self.update_treeview()

    #Compare local and comparison configs and update comparison attribute
    def do_comparison(self):
        #Check local config vs comparison config
        for full_key_path in self._local_data:

            #If the key is not found in the comparison config then add reason to comparison attribute
            if full_key_path not in self._comparison_data:
                self._local_data[full_key_path]['comparison']="Not found in default config"

            #Key has been found in both local and comparison configs
            #Check if value matches, update comparison attribute accordingly
            elif self._local_data[full_key_path]['value'] != self._comparison_data[full_key_path]['value']:
                print(f"Value Comparison - {self._local_data[full_key_path]['value']},{type(self._local_data[full_key_path]['value'])} compared to {self._comparison_data[full_key_path]['value']},{type(self._comparison_data[full_key_path]['value'])}")
                self._local_data[full_key_path]['comparison']="Value does not match default"
                self._local_data[full_key_path]['default_value']=self._comparison_data[full_key_path]['value']
            
            #Key has been found and value matches.  Set comparison attribute to blank.
            else:
                self._local_data[full_key_path]['comparison']=""
                self._local_data[full_key_path]['default_value']=self._comparison_data[full_key_path]['value']

        #Check comparison config vs local config
        #If comparison keys are missing from local config we need to add those keys and values and update comparison attribute accordingly
        for full_key_path in self._comparison_data:
            #If the key is not found in the local config then add reason to comparison attribute
            if full_key_path not in self._local_data:
                self._local_data[full_key_path]=self._comparison_data[full_key_path]
                self._local_data[full_key_path]['comparison']="Default not found in config"
                self._local_data[full_key_path]['default_value']=self._comparison_data[full_key_path]['value']
                self._local_data[full_key_path]['value']=""


    def update_treeview(self):
        #For each key in the local data
        for full_key_path in self._local_data:
            key_attributes=self._local_data[full_key_path]

            #For each subkey add a row to the tree
            #Add a child row for for each key value associated with the subkey
            if key_attributes['registry_type']=="subkey":

                if "comparison" not in key_attributes:
                    comparison_item=QStandardItem("")
                else:
                    comparison_item=QStandardItem(key_attributes['comparison'])

                    if key_attributes['comparison'] != "":
                        comparison_item.setBackground(QBrush(QColor(255, 0, 0)))
                    

                #Create parent tree item for this subkey
                parent_item = [QStandardItem(full_key_path),QStandardItem(''),QStandardItem(''),QStandardItem(''),comparison_item,QStandardItem(full_key_path),QStandardItem(full_key_path)]

                #Iterate the data again to check for key values matching this subkey
                row=0
                for subkey in self._local_data:
                    sub_key_path=os.path.split(subkey)[0]
                    new_key_name=os.path.split(subkey)[1]
                    key_attributes=self._local_data[subkey]

                    #Check if key value is from the correct subkey
                    if sub_key_path == full_key_path and key_attributes['registry_type']=="key_value":
                        key_name=QStandardItem(new_key_name)
                        key_value=QStandardItem(str(key_attributes['value']))
                        key_type=QStandardItem(key_attributes['type'])
                        full_key_path_qitem=QStandardItem(subkey)
                        sub_key_path_qitem=QStandardItem(sub_key_path)

                        if "comparison" not in key_attributes:
                            comparison_item=QStandardItem("")
                        else:
                            comparison_item=QStandardItem(key_attributes['comparison'])
                            if key_attributes['comparison'] != "":
                                comparison_item.setBackground(QBrush(QColor(255, 0, 0)))

                        if "default_value" not in key_attributes:
                            default_value_item=QStandardItem("")
                        else:
                            default_value_item=QStandardItem(str(key_attributes['default_value']))

                        #Create child for this key value and add to parent subkey
                        parent_item[0].setChild(row,0,key_name)
                        parent_item[0].setChild(row,1,key_type)
                        parent_item[0].setChild(row,2,key_value)
                        parent_item[0].setChild(row,3,default_value_item)
                        parent_item[0].setChild(row,4,comparison_item)
                        parent_item[0].setChild(row,5,full_key_path_qitem)
                        parent_item[0].setChild(row,6,sub_key_path_qitem)
                        row+=1

                #Append subkey and it's child key values to the treeview model
                self.appendRow(parent_item)

class CustomTreeProxyModel(QSortFilterProxyModel):
    def __init__(self, parent=None):
        super().__init__(parent)
        self._filters = dict()
        self.showDiffsOnly=False

    @property
    def filters(self):
        return self._filters
    
    @QtCore.pyqtSlot(bool)
    def showDiffsSlot(self,toggleState):
        print(f'Setting the filter to only show different values {toggleState}')
        self.showDiffsOnly=toggleState
        self.invalidateFilter()

        

    def filterAcceptsRow(self, source_row: int, source_parent: QModelIndex) -> bool:
        """ diffIdx = self.sourceModel().index(source_row, 4, source_parent) #The model holds a list of differences in col 5

        test=self.sourceModel().itemFromIndex(diffIdx)
        if test.text() != "":
            test.setBackground(QBrush(QColor(255, 0, 0)))
 """

        for column, expresion in self.filters.items():
            text = self.sourceModel().index(source_row, column, source_parent).data()
            regex = QRegExp(
                expresion, Qt.CaseInsensitive, QRegExp.RegExp
            )
            if regex.indexIn(text) == -1:
                return False
        return True
    
    def filterAcceptsColumn(self, source_column: int, source_parent: QModelIndex) -> bool:
        """ if source_column<=2:
            # Columns 0,1 & 2 are all we want to show, column 3 identifies if the values are different
            return True
        return False """
        return True
        

# ─────────────────────────────────────────────────────────────────────────────
# Column filter support for the validation table
# ─────────────────────────────────────────────────────────────────────────────

from PyQt5.QtWidgets import (QDialog, QVBoxLayout, QHBoxLayout, QLineEdit,
                             QPushButton, QLabel, QDialogButtonBox, QCheckBox,
                             QListWidget, QListWidgetItem, QAbstractItemView,
                             QHeaderView)
from PyQt5 import QtWidgets
from PyQt5.QtGui import QPainter, QIcon, QPixmap, QColor, QPen, QPolygon
from PyQt5.QtCore import QRect, QPoint, QSize


class ValidationProxyModel(QSortFilterProxyModel):
    """Multi-column filter proxy for the validation results table."""

    def __init__(self, parent=None):
        super().__init__(parent)
        self._filters = {}   # {col_index: str}

    def set_filter(self, col, text):
        if text:
            self._filters[col] = text.lower()
        elif col in self._filters:
            del self._filters[col]
        self.invalidateFilter()

    def clear_filter(self, col):
        self.set_filter(col, "")

    def clear_all_filters(self):
        self._filters.clear()
        self.invalidateFilter()

    def get_filter(self, col):
        return self._filters.get(col, "")

    def has_filter(self, col):
        return col in self._filters and bool(self._filters[col])

    def filterAcceptsRow(self, source_row, source_parent):
        for col, text in self._filters.items():
            idx = self.sourceModel().index(source_row, col, source_parent)
            cell = str(self.sourceModel().data(idx) or "").lower()
            if text not in cell:
                return False
        return True


class ColumnFilterDialog(QDialog):
    """Small dropdown-style dialog for filtering a single column."""

    def __init__(self, col, header_name, proxy_model, unique_values, parent=None):
        super().__init__(parent)
        self.col = col
        self.proxy = proxy_model
        self.setWindowTitle(f"Filter — {header_name}")
        self.setMinimumWidth(260)
        self.setWindowFlags(Qt.Popup | Qt.FramelessWindowHint)

        layout = QVBoxLayout(self)
        layout.setContentsMargins(8, 8, 8, 8)
        layout.setSpacing(6)

        # Search box
        self.line_search = QLineEdit()
        self.line_search.setPlaceholderText("Type to filter…")
        self.line_search.setText(proxy_model.get_filter(col))
        self.line_search.textChanged.connect(self._on_search_changed)
        layout.addWidget(self.line_search)

        # Unique value list
        self.value_list = QListWidget()
        self.value_list.setSelectionMode(QAbstractItemView.NoSelection)
        self.value_list.setMaximumHeight(180)
        self._all_values = sorted(set(str(v) for v in unique_values if v is not None))
        self._populate_list(self._all_values)
        self.value_list.itemClicked.connect(self._on_value_clicked)
        layout.addWidget(self.value_list)

        # Buttons
        btn_layout = QHBoxLayout()
        self.btn_clear = QPushButton("Clear Filter")
        self.btn_clear.clicked.connect(self._clear)
        self.btn_close = QPushButton("Close")
        self.btn_close.clicked.connect(self.accept)
        btn_layout.addWidget(self.btn_clear)
        btn_layout.addStretch()
        btn_layout.addWidget(self.btn_close)
        layout.addLayout(btn_layout)

        self.line_search.setFocus()

    def _populate_list(self, values):
        self.value_list.clear()
        current = self.proxy.get_filter(self.col)
        for v in values:
            item = QListWidgetItem(v)
            item.setFlags(item.flags() | Qt.ItemIsUserCheckable)
            item.setCheckState(Qt.Checked if v.lower() == current else Qt.Unchecked)
            self.value_list.addItem(item)

    def _on_search_changed(self, text):
        self.proxy.set_filter(self.col, text)
        # Filter the list display too
        filtered = [v for v in self._all_values if text.lower() in v.lower()]
        self._populate_list(filtered)

    def _on_value_clicked(self, item):
        # Clicking a value sets it as the exact filter
        self.line_search.setText(item.text())

    def _clear(self):
        self.line_search.clear()
        self.proxy.clear_filter(self.col)
        self._populate_list(self._all_values)


class FilterHeaderView(QHeaderView):
    """
    Paints a small funnel icon on the left of each section.
    Clicking the funnel area emits filter_clicked instead of sorting.
    Clicking elsewhere sorts as normal.
    """
    filter_clicked = QtCore.pyqtSignal(int)   # emits logical index

    _ICON_W     = 8
    _CLICK_ZONE = 12

    def __init__(self, orientation, parent=None):
        super().__init__(orientation, parent)
        self._active_filters: set = set()
        self.setSectionsClickable(True)
        self.setHighlightSections(True)

    def set_filtered_columns(self, indices: set):
        self._active_filters = set(indices)
        self.viewport().update()

    def mousePressEvent(self, e):
        if e.button() == Qt.LeftButton:
            logical = self.logicalIndexAt(e.pos())
            if logical >= 0:
                sec_x = self.sectionViewportPosition(logical)
                if e.x() <= sec_x + self._CLICK_ZONE:
                    self.filter_clicked.emit(logical)
                    return
        super().mousePressEvent(e)

    def paintSection(self, painter: QPainter, rect, logical_index: int):
        painter.save()
        super().paintSection(painter, rect, logical_index)
        painter.restore()
        self._draw_funnel(painter, rect, logical_index)

    def _draw_funnel(self, painter: QPainter, rect, logical_index: int):
        active = logical_index in self._active_filters
        ix = rect.left() + 3
        iy = rect.top() + (rect.height() - 10) // 2

        col = QColor("#0078d4") if active else QColor(160, 160, 160, 200)
        painter.save()
        painter.setRenderHint(QPainter.Antialiasing)
        painter.setPen(Qt.NoPen)
        painter.setBrush(col)

        top = QPolygon([
            QPoint(ix,                    iy),
            QPoint(ix + self._ICON_W,     iy),
            QPoint(ix + self._ICON_W - 2, iy + 3),
            QPoint(ix + 2,                iy + 3),
        ])
        painter.drawPolygon(top)
        painter.drawRect(ix + 3, iy + 3, 2, 4)
        painter.restore()