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
        