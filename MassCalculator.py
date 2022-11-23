
import sys
from os import path
from PyQt5 import QtCore, QtGui, QtWidgets, uic
from compound import Compound
import re
import csv
from time import strftime
from time import time
#from profilehooks import profile

#function for auto-py-to-exe
def resource_path(relative_path):
    """ Get absolute path to resource, works for dev and for PyInstaller """
    try:
        # PyInstaller creates a temp folder and stores path in _MEIPASS
        base_path = sys._MEIPASS
    except Exception:
        base_path = path.abspath(".")

    return path.join(base_path, relative_path)

class MainWindow(QtWidgets.QMainWindow):
    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)

        #load UI from main.ui
        uic.loadUi(resource_path("view/main.ui"), self)

        #default header items
        self.header_items = [HeaderItem('name'),
                HeaderItem('compound'),
                HeaderItem('neutral', charge = 0),
                HeaderItem('[M-H]-', charge= -1),
                HeaderItem('[M+H]+',  charge= 1),
                HeaderItem('[M+Na]+', adduct = 'Na', charge= 1),
                HeaderItem('[M+K]+', adduct = 'K', charge= 1)]


        #default mass precision
        self.mass_precision = 4

        #search matches
        self.search_term = ''
        self.matches = []

        #default elimination product
        self.elimination_product = 'H2O'

        #path to csv file
        self.save_path = ''

        #set UI Graphics
        self.init_UI()

        #set UI Actions
        self.set_actions()

        #undo and redo list will be empty at start 
        self.undo_list = [] 
        self.redo_list = []

        #check why table contents necessary!
        self.table_content = [[self.t1.item(r,c).text() for c in range(self.t1.columnCount())] for r in range(self.t1.rowCount())]

        #counter for undos
        self.undo_index = 0

        #adding one empty undo at start is necessary 
        self.add_undo('')

        #undo and paste Buttons in Menu are disabled at start
        self.actionUndo.setDisabled(True) 
        self.actionPaste.setDisabled(True)

        #temp cells to put in copy and cut cells before paste
        self.temp_cells = []

        #current state of the table 
        self.saved = [[self.t1.item(r,c).text() for c in range(self.t1.columnCount())] for r in range(self.t1.rowCount())] 
        
        #set a list of table items changed (only compound section)
        self.compounds_changed = [0,1]

        #self.inputBuilderCalculation.setText('2+1')
        #for i in range(0,100):
        #    self.add_complex_compound()
        
    #initially set up the UI
    def init_UI(self):
        #Application Title
        self.setWindowTitle('Exact Mass Calculator')

        #Application icon
        self.setWindowIcon(QtGui.QIcon(resource_path('view/atom.png')))
        
        #blue buttons
        for btn in (self.btnClearSearch, self.btnClearBuilder, self.btnClearColumn):
            btn.setStyleSheet('background-color:#7289DA; border-radius:4px; color:#FFFFFF') 
        
        #green buttons
        for btn in (self.btnAddBuilder, self.btnAddColumn):
            btn.setStyleSheet('background-color:#43B581; border-radius:4px; color:#FFFFFF')
        
        #red buttons
        self.btnCalculate.setStyleSheet('background-color:#43B581; border-radius:4px; color:#FFFFFF')#a95fde

        #yellow buttons
        self.btnFindSearch.setStyleSheet('background-color:#ffbf00; border-radius:4px; color:#FFFFFF')

        #white boxes behind the menu items
        self.lnMenu.setStyleSheet('border-radius:4px; background-color:#FFFFFF;')

        #input field blue border, white background, dark grey text
        for field in (self.inputNewColumnName, self.inputNewColumnModify, self.inputNewColumnCharge, self.inputNewColumnAdduct, self.inputBuilderName, self.inputBuilderCalculation, self.inputSearch):
            field.setStyleSheet('border-radius:4px;  color:#555555; border:2px solid #FFFFFF;')
        
        #dark grey text color in lblNewColumn and lblBuilder lblFind
        for label in (self.lblFind, self.lblNewColumn,  self.lblBuilder):
            label.setStyleSheet('color:#555555;')
        
        #set up and style Headers
        header = self.t1.horizontalHeader()
        header.setStyleSheet('border-radius:5px;')
        header.setSectionResizeMode(QtWidgets.QHeaderView.ResizeToContents)
        header.setMinimumSectionSize(120)
        header.setSectionsMovable(True)

        #font and background of table
        self.t1.setFont(QtGui.QFont ("Consolas", 12))
        self.t1.setStyleSheet('selection-background-color: #7289DA')

        #update table and header
        self.update_header()
        self.update_table()

        #Progress Bar
        self.progressBar.hide()

    #connect buttons with functions
    def set_actions(self):
        self.btnCalculate.clicked.connect(self.calculate)
        self.btnClearBuilder.clicked.connect(self.clear_builder)
        self.btnClearColumn.clicked.connect(self.clear_add_column)
        self.btnAddColumn.clicked.connect(self.add_column)
        self.btnAddBuilder.clicked.connect(self.add_complex_compound)
        self.btnFindSearch.clicked.connect(self.find)
        self.btnClearSearch.clicked.connect(self.clear_find)
        self.t1.minimumSizeHint()
        self.actionUndo.triggered.connect(self.undo)
        self.actionRedo.triggered.connect(self.redo)
        self.actionCopy.triggered.connect(self.copy_cells)
        self.actionCut.triggered.connect(self.cut_cells)
        self.actionPaste.triggered.connect(self.paste_cells)
        self.actionOpen.triggered.connect(self.open_csv)
        self.actionSave.triggered.connect(self.save_csv)
        self.actionSave_as.triggered.connect(self.save_as_csv)
        self.actionExit.triggered.connect(self.exit)
        self.actionDelete.triggered.connect(self.delete)
        self.actionAdd_Row.triggered.connect(self.add_row)
        self.actionDelete_Last_Row.triggered.connect(self.delete_last_row)
        self.actionMass_Precision.triggered.connect(self.get_mass_precision)
        self.actionElimination_Product.triggered.connect(self.get_elimination_product)
        self.actionHelp.triggered.connect(self.display_help)
        self.actionAbout_Mass_Calculator.triggered.connect(self.about)
        self.resizeEvent = self.resize_table
        self.WindowStateChange = self.resize_table
        self.actionRedo.setDisabled(True)
        self.actionUndo.setDisabled(True)
        self.actionSave.setDisabled(True)
        self.t1.itemChanged.connect(self.table_changed)
        self.t1.doubleClicked.connect(self.table_double_clicked)
        self.inputSearch.returnPressed.connect(self.find)


    #exit the app and check if save necessary 
    def exit(self):
        if self.saved == [[self.t1.item(r,c).text() for c in range(self.t1.columnCount())] for r in range(self.t1.rowCount())]:
            sys.exit(app)
        else:
            self.exit_save()     

    #catch close event
    def closeEvent(self, event):
        if self.saved == [[self.t1.item(r,c).text() for c in range(self.t1.columnCount())] for r in range(self.t1.rowCount())]:
            event.accept()
            sys.exit(app)
        else:
            event.ignore()
            self.exit_save()
    
    #ask for save if table changed before exit
    def exit_save(self):
        msgBox = QtWidgets.QMessageBox()
        msgBox.setWindowIcon(QtGui.QIcon(resource_path('atom.png')))
        msgBox.setWindowTitle('Save?')
        msgBox.setText('The table has been modified.')
        msgBox.setInformativeText('Do you want to save your changes?')
        msgBox.setStandardButtons(QtWidgets.QMessageBox.Save | QtWidgets.QMessageBox.Discard | QtWidgets.QMessageBox.Cancel)
        msgBox.setDefaultButton(QtWidgets.QMessageBox.Save)

        result = msgBox.exec_()
        if result == QtWidgets.QMessageBox.Save:
            self.save_csv()
            print('saved')
            sys.exit(app)
        elif result == QtWidgets.QMessageBox.Cancel:
            pass
        else:
            sys.exit(app)

    #Undo/Redo Functionality
    def add_undo(self, btn_text):
        self.actionUndo.setEnabled(True)
        self.table_content = [[self.t1.item(r,c).text() for c in range(self.t1.columnCount())] for r in range(self.t1.rowCount())]
        self.redo_list = []
        header_items = self.header_items[:]
        self.undo_list.append((self.table_content, header_items, btn_text, self.undo_index))
        if len(self.undo_list) > 10:
            self.undo_list = self.undo_list[-10::]
        self.undo_index += 1
        self.actionRedo.setDisabled(True)
        self.actionSave.setEnabled(True)

    #restore Table back to last undo
    def undo(self):
        if len(self.undo_list) > 1:
            self.t1.blockSignals(True)
            redo = self.undo_list.pop()
            self.redo_list.append(redo)
            undo = self.undo_list[-1]
            
            self.t1.clear()
            
            new_table = undo[0]
            self.header_items = undo[1]
            self.update_header()
            
            self.t1.setRowCount(len(new_table))
            self.t1.setColumnCount(len(undo[1]))
            self.t1.blockSignals(True)
            for r in range(len(new_table)):
                for c in range(len(new_table[0])):
                    item = QtWidgets.QTableWidgetItem()
                    item.setText(new_table[r][c])
                    if c > 1:
                        item.setTextAlignment(QtCore.Qt.AlignRight)
                    self.t1.setItem(r,c,item)
            self.t1.blockSignals(False)
            self.update_table()
            self.undo_done = True
            self.actionRedo.setEnabled(True)
            self.t1.blockSignals(False)
            if len(self.undo_list) == 1:
                self.actionUndo.setDisabled(True)
            for i in range(0, self.t1.rowCount()):
                if self.t1.item(i,1).text() != '' and self.t1.item(i,2).text() == '':
                    self.compounds_changed.append(i)

    #restore table back to last redo       
    def redo(self):
        if len(self.redo_list) > 0 and self.undo_done:
            self.t1.blockSignals(True)
            redo = self.redo_list.pop()
            self.undo_list.append(redo)
            self.t1.clear()
            new_table = redo[0]
            self.t1.setRowCount(len(new_table))
            self.t1.setColumnCount(len(new_table[0]))
            for r in range(len(new_table)):
                for c in range(len(new_table[0])):
                    item = QtWidgets.QTableWidgetItem()
                    item.setText(new_table[r][c])
                    if c > 1:
                        item.setTextAlignment(QtCore.Qt.AlignRight)
                    self.t1.setItem(r,c,item)
            self.header_items = redo[1]
            self.update_header()
            self.update_table()
            self.undo_done = True
            self.t1.blockSignals(False)
            self.actionUndo.setEnabled(True)
            if len(self.redo_list) == 0:
                self.actionRedo.setDisabled(True)

    #Table related Functions
    #if something in table changed check if data is unsaved
    def table_changed(self, item):
        
        column = item.column()
        row = item.row() +1
        row_count = self.t1.rowCount()

        if row == row_count:
            self.t1.insertRow(row)

        if column == 1:
            self.compounds_changed.append(row-1)

        self.update_table()
        if self.saved == [[self.t1.item(r,c).text() for c in range(self.t1.columnCount())] for r in range(self.t1.rowCount())]:
            self.setWindowTitle('Exact Mass Calculator   -   ' + self.save_path.split('/')[-1])
        elif self.save_path == '':
            self.setWindowTitle('Exact Mass Calculator   -   *')
        else:
            self.setWindowTitle('Exact Mass Calculator   -   ' + self.save_path.split('/')[-1]+'*')
            self.actionSave.setEnabled(True)
        self.add_undo('Edit Table')

    #dont want empty cells in table, put empty item into each cell
    def update_table(self):
        self.t1.blockSignals(True)
        for i in range(self.t1.rowCount()):
            for j in range(len(self.header_items)):
                if not self.t1.item(i,j):
                    item = QtWidgets.QTableWidgetItem()
                    if j > 2:
                        item.setTextAlignment(QtCore.Qt.AlignRight)
                    self.t1.setItem(i, j, item)
        self.t1.blockSignals(False)

    #update each header item, font, style
    def update_header(self):
        self.t1.blockSignals(True)
        fnt = QtGui.QFont()
        fnt.setPointSize(14)
        fnt.setBold(True)
        fnt.setFamily("Consolas")  
        header_count = len(self.header_items)
        self.t1.setColumnCount(header_count)
        for i in range(0, len(self.header_items)):
            item = QtWidgets.QTableWidgetItem(self.header_items[i].name)
            item.setFont(fnt)
            item.setForeground(QtGui.QBrush(QtGui.QColor(85, 85, 85)))
            self.t1.setHorizontalHeaderItem(i, item)
            
        self.update_table()
        self.t1.blockSignals(False)
    
    #change the size of table after window size has been changed
    def resize_table(self, event):
        width = self.size().width()
        height = self.size().height()
        self.t1.setGeometry(190,10, width - 200, height - 50)

    #take the in inputs from new column and add new header item accordingly  
    def add_column(self):
        self.inputNewColumnModify.setStyleSheet('border-radius:4px; color:#555555; border:2px solid #FFFFFF')
        self.inputNewColumnAdduct.setStyleSheet('border-radius:4px; color:#555555; border:2px solid #FFFFFF')
        self.inputNewColumnCharge.setStyleSheet('border-radius:4px; color:#555555; border:2px solid #FFFFFF')
        if self.inputNewColumnModify.text() != '' or self.inputNewColumnCharge.text() != '' or self.inputNewColumnAdduct.text() != '':
            try:
                add = ''
                delete = ''
                adduct = ''
                if self.inputNewColumnModify.text() != '':
                    find_plus = re.findall(r'\+[A-Z0-9]+', self.inputNewColumnModify.text())
                    find_minus = re.findall(r'\-[A-Z0-9]+', self.inputNewColumnModify.text())
                    add = ''.join([a[1:] for a in find_plus])
                    delete = ''.join([d[1:] for d in find_minus])

                    if sorted(''.join(find_plus)+''.join(find_minus)) != sorted(self.inputNewColumnModify.text()):
                        self.inputNewColumnModify.setStyleSheet('border-radius:4px; color:#f04747; border:2px solid #FFFFFF')
                        return
                
                if self.inputNewColumnCharge.text() == '0' or self.inputNewColumnCharge.text() == '':
                    charge = 0
                else:
                    charge_amount = re.search(r'\d+', self.inputNewColumnCharge.text())
                    charge_polarity = re.search(r'(\-|\+)', self.inputNewColumnCharge.text())
                    if charge_amount == None and charge_polarity.group() == '+':
                        charge = 1
                    elif charge_amount == None and charge_polarity.group() == '-':
                        charge = -1
                    else:
                        charge = int(charge_polarity.group()+charge_amount.group())
                
                if self.inputNewColumnAdduct.text() != '' and self.inputNewColumnAdduct.text() in ['K', 'Na', 'Li'] and charge > 0:
                    adduct = self.inputNewColumnAdduct.text()
                elif self.inputNewColumnAdduct.text() not in ['K', 'Na', 'Li','']:
                    self.inputNewColumnAdduct.setStyleSheet('border-radius:4px; color:#f04747; border:2px solid #FFFFFF')
                    return
                elif self.inputNewColumnAdduct.text() in ['K', 'Na', 'Li'] and charge <= 0:
                    self.inputNewColumnAdduct.setStyleSheet('border-radius:4px; color:#f04747; border:2px solid #FFFFFF')
                    self.inputNewColumnCharge.setStyleSheet('border-radius:4px; color:#f04747; border:2px solid #FFFFFF')
                    return


                
                if self.inputNewColumnName.text() == '':
                    if charge == 1:
                        charge_display = ''
                    elif charge == -1:
                        charge_display = '-'
                    else:
                        charge_display = charge
                    if len(add) > 0:
                        name_add = '+'+add
                    else:
                        name_add = ''
                    if len(delete) > 0:
                        name_delete = '-'+delete
                    else:
                        name_delete = ''

                    if adduct != '':
                        name = f'[M{name_add}{name_delete}+{charge_display}{adduct}]{charge_display}+'
                    elif charge == 0:
                        name = f'[M{name_add}{name_delete}]'
                    elif charge >= 1:
                        polarity = charge_polarity.group()
                        name = f'[M{name_add}{name_delete}{polarity}{charge_display}H]{charge_display}{polarity}'
                    elif charge <= -1:
                        polarity = charge_polarity.group()
                        name = f'[M{name_add}{name_delete}{charge_display}H]{str(charge_display)[1:]}{polarity}'
                else:
                    name = self.inputNewColumnName.text()
                
                self.header_items.append(HeaderItem(name, add = add, delete = delete, adduct = adduct, charge = charge))
                
                self.update_header()
                for i in range(0, self.t1.rowCount()):
                    self.compounds_changed.append(i)
                self.add_undo('Add Column')
                
            except:
                self.inputNewColumnCharge.setStyleSheet('border-radius:4px; color:#f04747; border:2px solid #FFFFFF')

        elif self.inputNewColumnName.text() != '':
            print('New retention time will be added')
            self.header_items.append(HeaderItem(name=self.inputNewColumnName.text(), rt = 'yes'))
            self.update_header()
            for i in range(0, self.t1.rowCount()):
                item = QtWidgets.QTableWidgetItem()
                item.setText('')
                item.setTextAlignment(QtCore.Qt.AlignRight)
                self.t1.setItem(i, self.t1.columnCount()-1, item)

    #clears the input fields in add column    
    def clear_add_column(self):
        self.inputNewColumnName.setText('')
        self.inputNewColumnModify.setText('')
        self.inputNewColumnCharge.setText('')
        self.inputNewColumnAdduct.setText('')
        self.inputNewColumnModify.setStyleSheet('border-radius:4px; color:#555555; border:2px solid #FFFFFF')
        self.inputNewColumnAdduct.setStyleSheet('border-radius:4px; color:#555555; border:2px solid #FFFFFF')
        self.inputNewColumnCharge.setStyleSheet('border-radius:4px; color:#555555; border:2px solid #FFFFFF')

    #add a row to the table, default at the end or if row is selected below it
    def add_row(self):       
        self.t1.blockSignals(True)
        indexes = self.t1.selectionModel().selectedRows()
        if indexes:
            row_pos = indexes[-1].row() + 1
        else:
            row_pos = self.t1.rowCount()
        self.t1.insertRow(row_pos)
        self.update_table()
        for i in range(2, len(self.header_items)):
            
            self.t1.item(row_pos, i).setFlags(QtCore.Qt.ItemIsEnabled)
            
        self.add_undo('Add Row')
        self.t1.blockSignals(False)
    
    #deletes the last row
    def delete_last_row(self):
        row_pos = self.t1.rowCount()
        if row_pos > 0:
            self.t1.removeRow(row_pos-1)
            self.add_undo('Delete Last Row')

    #deletes selected columns or rows
    def delete(self):
        
        rows = self.t1.selectionModel().selectedRows()
        rows.sort()
        columns = self.t1.selectionModel().selectedColumns()
        columns.sort()
        for r in rows[::-1]:
            self.t1.removeRow(r.row())
        columns = self.t1.selectionModel().selectedColumns()
        columns.sort()
        for c in columns[::-1]:
            if c.column() > 2:
                self.t1.removeColumn(c.column())
                del self.header_items[c.column()]
        #if len(rows) > 0 or len(columns) > 0:
        
        indexes = [index for index in self.t1.selectedIndexes()]
        self.t1.blockSignals(True)
        for index in indexes:
            row = index.row()
            column = index.column()
            self.t1.item(row, column).setText('')
            self.t1.item(row,column).setForeground(QtGui.QBrush(QtGui.QColor(0, 0, 0)))
        self.t1.blockSignals(False)
        if len(rows) > 0 or len(columns) > 0 or len(indexes) > 0:
            self.add_undo('Delete')
    
    #get cell content from selected rows, columns indexes and put in list
    def cells_from_indexes(self, indexes):
        cells = []
        start_row = indexes[0].row()
        start_column = indexes[0].column()
        #indexes = indexes[1:]
        for index in indexes:
            text = self.t1.item(index.row(), index.column()).text()
            row = index.row() - start_row
            col = index.column() - start_column
            cells.append((row, col, text))
        return cells

    def table_double_clicked(self, mi):
        row = mi.row()
        column = mi.column()
        if self.t1.item(row, column).text() != '':
            cb = QtWidgets.QApplication.clipboard()
            cb.clear(mode=cb.Clipboard )
            cb.setText(self.t1.item(row, column).text(), mode=cb.Clipboard)

    #copy cells into temp_cells without deleting selected cells
    def copy_cells(self):
        indexes = [index for index in self.t1.selectedIndexes()]
        if len(indexes) == 0:
            return
        self.temp_cells = self.cells_from_indexes(indexes)
        self.actionPaste.setEnabled(True)
    
    #copy cells into temp_cells and delete selected cells
    def cut_cells(self):
        indexes = [index for index in self.t1.selectedIndexes()]
        if len(indexes) == 0:
            return
        self.temp_cells = self.cells_from_indexes(indexes)
        self.t1.blockSignals(True)
        for index in indexes:
            row = index.row()
            column = index.column()
            self.t1.item(row, column).setText('')
            self.compounds_changed.append(row)
        self.t1.blockSignals(False)
        self.add_undo('Cut')
        self.actionPaste.setEnabled(True)

    #put cells from temp_cells into table beginning from new selected cell
    def paste_cells(self):
        try:
            start_cell = [index for index in self.t1.selectedIndexes()][0]
            start_row = start_cell.row()
            start_column = start_cell.column()
            self.t1.blockSignals(True)
            for cell in self.temp_cells:
                self.t1.item(start_row + cell[0], start_column + cell[1]).setText(cell[2])
                self.compounds_changed.append(start_row + cell[0])
            self.t1.blockSignals(False)
            self.temp_cells = []
            self.add_undo('Paste')
            self.actionPaste.setDisabled(True)
        except:
            return

    #Calculate the Masses in Table
    def calculate(self):
        t0 = time()
        self.t1.blockSignals(True)
        self.progressBar.show()
        counter = 0
        num_calcs = len(set(self.compounds_changed))
        index = 1

        for i in set(self.compounds_changed):
            
            counter = int((index/num_calcs)*100)
            index += 1
            
            error = False
            if self.t1.item(i,1).text():
                comp = Compound(self.t1.item(i,1).text())
                item = self.t1.item(i,1).setForeground(QtGui.QBrush(QtGui.QColor(0, 0, 0)))
                if not comp.check_formula():
                    item = self.t1.item(i,1).setForeground(QtGui.QBrush(QtGui.QColor(240, 71, 71)))
                    for j in range(2, len(self.header_items)):
                        item = QtWidgets.QTableWidgetItem()
                        item.setText('')
                        self.t1.setItem(i,j,item)
                    error = True
                self.t1.clearSelection()
                for j in range(2, len(self.header_items)):
                    if self.header_items[j].rt == 'no':
                        if error == True:
                            break
                        
                        new_comp = Compound(self.t1.item(i,1).text(),
                                            charge = int(self.header_items[j].charge),
                                            adduct = self.header_items[j].adduct).del_elements(self.header_items[j].delete).add_elements(self.header_items[j].add)
                        if new_comp.elements == 'invalid formula':
                            item = QtWidgets.QTableWidgetItem()
                            item.setText('N/A')
                            item.setTextAlignment(QtCore.Qt.AlignCenter)
                        else:
                            item = QtWidgets.QTableWidgetItem()
                            try:
                                item.setText(str(new_comp.calc_mass(round_by=self.mass_precision)))
                            except:
                                item.setText('---')
                            item.setTextAlignment(QtCore.Qt.AlignRight)

                        item.setFlags(QtCore.Qt.ItemIsEnabled)
                        self.t1.setItem(i,j,item) #setItem very slow
            else:
                for j in range(2, len(self.header_items)):
                    self.t1.item(i,j).setText('')
            self.progressBar.setValue(counter)
        self.t1.blockSignals(False)
        self.update_table()
        self.add_undo('Calculate')
        self.compounds_changed = []
        self.progressBar.setValue(0)
        self.progressBar.hide()
    
    #open window to set mass precision and update accordingly
    def get_mass_precision(self):
        def show_warning_text(x):
            if not x.text().isnumeric():
                x.setStyleSheet('border-radius:5px; background-color:#FFFFFF; color:#f04747; border:2px solid #FFFFFF')
            else:
                x.setStyleSheet('border-radius:5px; background-color:#FFFFFF; color:#555555; border:2px solid #FFFFFF')
            fnt = QtGui.QFont()
            fnt.setPointSize(12)
            fnt.setBold(True)
            fnt.setFamily("Arial")
            x.setFont(fnt)

        w = MassPrecisionDialog()
        w.lineEdit.setText(str(self.mass_precision))
        w.lineEdit.textChanged.connect(lambda x: show_warning_text(x = w.lineEdit))
        try:
            if w.lineEdit.textChanged != self.mass_precision:
                self.mass_precision = w.getResults()
                for i in range(0, self.t1.rowCount()):
                    self.compounds_changed.append(i)
                self.calculate()
        except ValueError:
            self.mass_precision = self.mass_precision

    #Compound Builder Functions
    #take input from compound builder, calculate new compound and put it in table
    def add_complex_compound(self):
        self.inputBuilderCalculation.setStyleSheet('border-radius:5px; background-color:#FFFFFF; color:#555555; border:2px solid #FFFFFF')
        
        to_add = []
        to_del = []
        compounds = self.inputBuilderCalculation.text()
        if re.search(r'[^\+\-\*0-9]', compounds):
            self.inputBuilderCalculation.setStyleSheet('border-radius:4px; color:#f04747; border:2px solid #FFFFFF')

        plus = [m.group(2) for m in re.finditer(r'(\+|^)([\d]+\*[\d]+|[\d]+)', compounds)]
        minus = [m.group(1) for m in re.finditer(r'\-([\d]+\*[\d]+|[\d]+)', compounds)]

        if len(plus) + len(minus) == 0:
            return

        auto_name = ''
        try:
            for item in plus:
                if '*' in item:
                    i, j = item.split('*')
                    temp = Compound(self.t1.item(int(i)-1,1).text()).multiply(int(j))
                    auto_name += '+'+str(j)+'('+self.t1.item(int(i)-1,0).text()+')'
                    
                else:
                    temp = Compound(self.t1.item(int(item)-1,1).text())
                    auto_name += '+'+'('+self.t1.item(int(item)-1,0).text()+')'
                to_add.append(temp)
                if temp.formula == '':
                    self.inputBuilderCalculation.setStyleSheet('border-radius:4px; color:#f04747; border:2px solid #FFFFFF')
                    return
            
            for item in minus:
                if '*' in item:
                    
                    i, j = item.split('*')
                    temp = Compound(self.t1.item(int(i)-1,1).text()).multiply(int(j))
                    auto_name += '-'+str(j)+'('+self.t1.item(int(i)-1,0).text()+')'
                else:
                    temp = Compound(self.t1.item(int(item)-1,1).text())
                    auto_name += '-'+'('+self.t1.item(int(item)-1,0).text()+')'
                to_del.append(temp)
                if temp.formula == '':
                    self.inputBuilderCalculation.setStyleSheet('border-radius:4px; color:#f04747; border:2px solid #FFFFFF')
                    return
                 
        except AttributeError:
            print('Attribute Error, None Type object has no attribute (index!)')
            self.inputBuilderCalculation.setStyleSheet('border-radius:4px; color:#f04747; border:2px solid #FFFFFF')
     

        try:
            compound = Compound(to_add.pop().formula)
        except IndexError:
            return
        for c in to_add:
            compound = compound.add_compound(c, elimination=self.elimination_product)
        for c in to_del:
            try:
                compound = compound.del_compound(c, elimination=self.elimination_product)
            except:
                self.inputBuilderCalculation.setStyleSheet('border-radius:5px; background-color:#FFFFFF; color:#f04747; border:2px solid #FFFFFF')
                return

        for i in range(self.t1.rowCount()):
            if self.t1.item(i,0).text() == '' and self.t1.item(i,1).text() == '':
                index = i
                break
            elif i == self.t1.rowCount()-1:
                index = i+1
                self.t1.insertRow(index)
                self.update_table()

        if index == self.t1.rowCount() -1:
            self.t1.insertRow(index+1)

        compound.name = self.inputBuilderName.text()
        self.update_table()
        self.t1.blockSignals(True)
        if compound.name != '':
            self.t1.item(index,0).setText(compound.name)
        else:
            self.t1.item(index,0).setText(auto_name[1:])
        self.t1.item(index,1).setText(compound.formula)
        self.compounds_changed.append(index)
        self.t1.blockSignals(False)
        self.add_undo('Add Compound')

    #open window to set option for elimination product and update it accordingly
    def get_elimination_product(self):
        def show_warning_text(x):
            comp = Compound(x.text())
            if not comp.check_formula():
                x.setStyleSheet('border-radius:5px; background-color:#FFFFFF; color:#f04747; border:2px solid #FFFFFF')
            else:
                x.setStyleSheet('border-radius:5px; background-color:#FFFFFF; color:#555555; border:2px solid #FFFFFF')
            fnt = QtGui.QFont()
            fnt.setPointSize(12)
            fnt.setBold(True)
            fnt.setFamily("Arial")
            x.setFont(fnt)

        w = EliminationProductDialog()
        w.lineEdit.setText(str(self.elimination_product))
        w.lineEdit.textChanged.connect(lambda x: show_warning_text(x = w.lineEdit))
        result = w.getResults()
        comp = Compound(w.lineEdit.text())
        if comp.check_formula():
            self.elimination_product = result
        else:
            self.elimination_product = self.elimination_product
    
    #clear input fields for compound builder
    def clear_builder(self):
        self.inputBuilderName.setText('')
        self.inputBuilderCalculation.setText('')
        self.inputBuilderCalculation.setStyleSheet('border-radius:5px; background-color:#FFFFFF; color:#555555; border:2px solid #FFFFFF')

    #Save and Open Files
    #spawn open file dialog and select csv file, fill table with contents of that file
    def open_csv(self):
        if self.saved != [[self.t1.item(r,c).text() for c in range(self.t1.columnCount())] for r in range(self.t1.rowCount())]:
            msgBox = QtWidgets.QMessageBox()
            msgBox.setWindowIcon(QtGui.QIcon(resource_path('atom.png')))
            msgBox.setWindowTitle('Save?')
            msgBox.setText('The table has been modified.')
            msgBox.setInformativeText('Do you want to save your changes?')
            msgBox.setStandardButtons(QtWidgets.QMessageBox.Save | QtWidgets.QMessageBox.Discard | QtWidgets.QMessageBox.Cancel)
            result = msgBox.exec_()
            if result == QtWidgets.QMessageBox.Save:
                self.save_csv()
            elif result == QtWidgets.QMessageBox.Cancel:
                pass
        options = QtWidgets.QFileDialog.Options()
        options |= QtWidgets.QFileDialog.DontUseNativeDialog
        fileName, _ = QtWidgets.QFileDialog.getOpenFileName(self,"Open", "","CSV Files (*.csv)", options=options)
        if fileName:
            self.save_path = fileName
            
            with open(fileName, 'r', encoding = 'utf-8') as csvfile:
                reader = csv.reader(csvfile, delimiter = ',')
                
                while len(self.header_items) > 3:
                    self.header_items.pop()
                headers = next(reader)
                for i in range(3, len(headers)):
                    content = headers[i].split('#')
                    try:
                        self.header_items.append(HeaderItem(content[0], add=content[1], delete=content[2], adduct=content[3], charge=content[4], rt = content[5]))
                    except IndexError:
                        self.header_items.append(HeaderItem(content[0], add=content[1], delete=content[2], adduct=content[3], charge=content[4], rt = 'no'))
                
                self.update_header()
                self.update_table()
                self.t1.setRowCount(0)
                row_count = 0
                for row in reader:
                    count = self.t1.rowCount()
                    self.t1.insertRow(count)
                    for column in range(len(row)):
                        item = QtWidgets.QTableWidgetItem()
                        item.setText(row[column])
                        if column > 1 and self.header_items[column].rt == 'no':
                            item.setFlags(QtCore.Qt.ItemIsEnabled)
                        try:
                            float(row[column])
                            item.setTextAlignment(QtCore.Qt.AlignRight)
                        except ValueError:
                            item.setTextAlignment(QtCore.Qt.AlignLeft)
                        if self.header_items[column].rt == 'yes':
                            item.setTextAlignment(QtCore.Qt.AlignRight)
                            #item.setBackground(QtGui.QColor(255,0,0))
                        self.t1.setItem(row_count,column,item)
                    row_count += 1
                
                self.setWindowTitle('Exact Mass Calculator   -   ' + fileName.split('/')[-1])
                
                self.update_table()
                self.saved = [[self.t1.item(r,c).text() for c in range(self.t1.columnCount())] for r in range(self.t1.rowCount())]
                self.table_content = [[self.t1.item(r,c).text() for c in range(self.t1.columnCount())] for r in range(self.t1.rowCount())]
                self.undo_list = []
                self.compounds_changed = []
                self.calculate()
                self.add_undo('')
                self.actionUndo.setDisabled(True)
                self.actionRedo.setDisabled(True)
                self.actionSave.setDisabled(True)

    #save file if it has been saved before
    def save_csv(self):
            options = QtWidgets.QFileDialog.Options()
            options |= QtWidgets.QFileDialog.DontUseNativeDialog
            if self.save_path != '':
                fileName = self.save_path
            else:
                fileName, _ = QtWidgets.QFileDialog.getSaveFileName(self,"Save as","","CSV Files (*.csv)", options=options)
                self.save_path = fileName
            try:
                with open(fileName, 'w', newline = '', encoding = 'utf-8') as csvfile:
                    writer = csv.writer(csvfile, delimiter = ',')
                    headers = ['name', 'compound', 'neutral']
                    for column in range(3, self.t1.columnCount()):
                        header = self.header_items[column]
                        content = header.name+'#'+header.add+'#'+header.delete+'#'+header.adduct+'#'+str(header.charge)+'#'+header.rt
                        headers.append(content)
                    writer.writerow(headers)
                    for row in range(self.t1.rowCount()):
                        rowdata = []
                        for column in range(self.t1.columnCount()):
                            item = self.t1.item(row, column)
                            if item is not None:
                                rowdata.append(item.text())
                            else:
                                rowdata.append('')
                        writer.writerow(rowdata)
                self.setWindowTitle('Exact Mass Calculator   -   ' + fileName.split('/')[-1])
                self.statusBar().showMessage('Saved File as '+fileName +strftime('    %H:%M'))
                self.saved = [[self.t1.item(r,c).text() for c in range(self.t1.columnCount())] for r in range(self.t1.rowCount())]
                self.actionSave.setDisabled(True)
            except FileNotFoundError:
                print('File Path Not Found')

    #select a new file to save content to and save it
    def save_as_csv(self):
        options = QtWidgets.QFileDialog.Options()
        options |= QtWidgets.QFileDialog.DontUseNativeDialog
        fileName, _ = QtWidgets.QFileDialog.getSaveFileName(self,"Save as","untitled.csv","CSV Files (*.csv)", options=options)
        if not fileName.endswith('.csv'):
            fileName += '.csv'
        self.save_path = fileName
        if fileName:
            with open(fileName, 'w', newline = '', encoding='utf-8') as csvfile:
                    writer = csv.writer(csvfile, delimiter = ',')
                    headers = ['name', 'compound', 'neutral']
                    for column in range(3, self.t1.columnCount()):
                        header = self.header_items[column]
                        content = header.name+'#'+header.add+'#'+header.delete+'#'+header.adduct+'#'+str(header.charge)+'#'+header.rt
                        headers.append(content)
                    writer.writerow(headers)
                    for row in range(self.t1.rowCount()):
                        rowdata = []
                        for column in range(self.t1.columnCount()):
                            item = self.t1.item(row, column)
                            if item is not None:
                                rowdata.append(item.text())
                            else:
                                rowdata.append('')
                        writer.writerow(rowdata)
            self.setWindowTitle('Exact Mass Calculator   -   ' + fileName.split('/')[-1])
            self.statusBar().showMessage('Saved File as '+fileName +strftime('    %H:%M'))
            self.saved = [[self.t1.item(r,c).text() for c in range(self.t1.columnCount())] for r in range(self.t1.rowCount())]
            self.actionSave.setDisabled(True)

    #Find Items in Table
    def find(self): 
        
        if self.inputSearch.text() != self.search_term and self.inputSearch.text() != '':
            self.search_term = self.inputSearch.text()
            self.matches = []
            self.t1.blockSignals(True)
            for row in range(self.t1.rowCount()):
                for column in range(self.t1.columnCount()):
                    self.t1.item(row, column).setBackground(QtGui.QColor(255,255,255))
                    if self.inputSearch.text().lower() in self.t1.item(row, column).text().lower():
                            self.t1.item(row, column).setBackground(QtGui.QColor(255, 191, 0))
                            self.matches.append((row, column))


            self.matches.reverse()
            try:
                match = self.matches.pop()
                self.t1.scrollToItem(self.t1.item(match[0], match[1]))
                self.inputSearch.setStyleSheet('border-radius:4px;  color:#555555; border:2px solid #FFFFFF;')
            except IndexError:
                self.inputSearch.setStyleSheet('border-radius:4px;  color:#f04747; border:2px solid #FFFFFF;')
            
        else:
            if len(self.matches) > 0:
                match = self.matches.pop()
                self.t1.scrollToItem(self.t1.item(match[0], match[1]))

        self.t1.blockSignals(False)

    #clear input field for search 
    def clear_find(self):
        self.t1.blockSignals(True)
        for row in range(self.t1.rowCount()):
            for column in range(self.t1.columnCount()):
                self.t1.item(row, column).setBackground(QtGui.QColor(255,255,255))
                self.inputSearch.setText('')
        self.matches = []
        self.search_term = ''
        self.t1.blockSignals(False)

    #Display Help/Error Dialogs
    def display_help(self):
        w = HelpDialog()
        w.exec_()

    #display about App Window
    def about(self):
        msgBox = QtWidgets.QMessageBox()
        msgBox.setWindowIcon(QtGui.QIcon(resource_path('atom.png')))
        msgBox.setWindowTitle('About Mass Calculator')
        msgBox.setText('Exact Mass Calculator')
        msgBox.setInformativeText('Version 2.0\n\nA graphical tool to calculate exact masses of chemical compounds for Mass Spectronomy.\n\nAxel Walter, 2020')
        msgBox.exec_()

class MassPrecisionDialog(QtWidgets.QDialog):
    def __init__(self):
        super(MassPrecisionDialog, self).__init__()
        uic.loadUi(resource_path("view/mass_precision_dialog.ui"), self)
        self.setWindowIcon(QtGui.QIcon(resource_path('atom.png')))
        self.setWindowTitle('Mass Precision')
        self.setUI()

    def setUI(self):
        self.line.setStyleSheet('background-color:#FFFFFF; border-radius:1px;')
        for button in self.buttonBox.buttons():
            button.setStyleSheet('width:80px; height: 40px; background-color:#7289DA; border-radius:4px; color:#FFFFFF; height: 32px;')
        self.label.setStyleSheet('color:#555555;')
        self.lineEdit.setStyleSheet('border-radius:4px; background-color:#EEEEEE; color:#555555; border:2px solid #FFFFFF')
        self.setWindowFlags(QtCore.Qt.WindowCloseButtonHint)
        x = win.geometry().x()
        y = win.geometry().y()
        self.move(x+250,y+150)
        

    def getResults(self):
        if self.exec_() == QtWidgets.QDialog.Accepted:
            mass_precision = int(self.lineEdit.text())
            return mass_precision
        else:
            return win.mass_precision

class EliminationProductDialog(QtWidgets.QDialog):
    def __init__(self):
        super(EliminationProductDialog, self).__init__()
        uic.loadUi(resource_path("view/elimination_product_dialog.ui"), self)
        self.setWindowIcon(QtGui.QIcon(resource_path('atom.png')))
        self.setWindowTitle('Elimination Product')
        self.setUI()

    def setUI(self):
        self.line.setStyleSheet('background-color:#FFFFFF; border-radius:1px;')
        for button in self.buttonBox.buttons():
            button.setStyleSheet('width:80px; height: 40px; background-color:#7289DA; border-radius:4px; color:#FFFFFF; height:32px;')
        self.label.setStyleSheet('color:#555555;')
        self.label_2.setStyleSheet('color:#555555;')
        self.lineEdit.setStyleSheet('border-radius:4px; background-color:#EEEEEE; color:#555555; border:2px solid #FFFFFF')
        self.setWindowFlags(QtCore.Qt.WindowCloseButtonHint)
        x = win.geometry().x()
        y = win.geometry().y()
        self.move(x+250,y+150)

    def getResults(self):
        if self.exec_() == QtWidgets.QDialog.Accepted:
            elimination_product = self.lineEdit.text()
            return elimination_product
        else:
            return win.elimination_product

class HelpDialog(QtWidgets.QDialog):
    def __init__(self):
        super(HelpDialog, self).__init__()
        uic.loadUi(resource_path("view/help_dialog.ui"), self)
        self.setWindowIcon(QtGui.QIcon(resource_path('atom.png')))
        self.setWindowTitle('Help')
        self.setUI()

    def setUI(self):
        self.textBrowser.setStyleSheet('color:#555555; background-color:#FFFFFF; border-radius:1px;')
        self.setWindowFlags(QtCore.Qt.WindowCloseButtonHint)
        x = win.geometry().x()
        y = win.geometry().y()
        self.move(x+250,y+150)

class HeaderItem():
    def __init__(self, name, add='', delete ='', adduct = '', charge='', rt = 'no'):
        self.name = name 
        self.add = add
        self.delete = delete
        self.adduct = adduct
        self.charge = charge
        self.rt = rt
        

app = QtWidgets.QApplication(sys.argv)
win = MainWindow()
win.show()
app.exec_()

#TODO

#set Color of columns RT, POS, NEG when open and calc and update table
