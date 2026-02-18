import sys
import json
import os
import subprocess
import ast
import uuid
from PyQt5.QtWidgets import (QApplication, QMainWindow, QFileDialog, QInputDialog,QWidget, QVBoxLayout, QHBoxLayout,
                             QPushButton, QListWidget, QSplitter, QLabel, QListWidgetItem,
                             QMessageBox, QDialog, QAction, QActionGroup, QUndoStack)
from PyQt5.QtCore import Qt, QPointF,QSettings
from PyQt5.QtGui import QColor, QPalette, QKeySequence



from graphics.code_block import CodeBlock
from graphics.connection import Connection


from ui.function_search_dialog import FunctionSearchDialog
from ui.directory_tab import DirectoryTab
from ui.info_dialog import InfoDialog
from ui.image_picker import ImagePickerDialog

from commands.graph_commands import (AddBlockCommand, DeleteBlockCommand, 
                                      AddConnectionCommand, DeleteConnectionCommand,
                                      MoveBlockCommand, RenameBlockCommand)



class CodeGraphWindow(QMainWindow):
    """Main application window"""
    
    def __init__(self):
        super().__init__()
        
        self.current_file = None
        self.directory_data = {}
        self.current_directory = "root"
        self.directory_tabs = {}
        self.root_path = None
        
        # Undo stack
        self.undo_stack = QUndoStack(self)
        
        # Load settings
        self.settings = QSettings('CodeGrapher', 'CodeGrapherApp')
        self.current_theme = self.settings.value('theme', 'light')
        
        self.init_ui()
        self.apply_theme(self.current_theme)
        
        # Prompt for root folder
        self.prompt_root_path()
        # Auto load if codegraph.cg exists
        self.auto_load_codegraph()

    def init_ui(self):
        """Initialize the UI"""
        self.setWindowTitle('CodeGrapher - Visual Code Navigator')
        self.setGeometry(100, 100, 1400, 900)
        
        central_widget = QWidget()
        self.setCentralWidget(central_widget)
        
        main_layout = QHBoxLayout()
        
        splitter = QSplitter(Qt.Horizontal)
        
        self.sidebar = self.create_sidebar()
        splitter.addWidget(self.sidebar)
        
        self.main_area = QWidget()
        self.main_layout = QVBoxLayout()
        self.main_area.setLayout(self.main_layout)
        splitter.addWidget(self.main_area)
        
        splitter.setSizes([200, 1200])
        
        main_layout.addWidget(splitter)
        central_widget.setLayout(main_layout)
        
        self.create_menu_bar()
        
        self.statusBar().showMessage('Ready - Middle-click to pan | Click dots to connect')
    
    def auto_load_codegraph(self):
        """Auto-load codegraph.cg if found"""
        # Check in current directory
        codegraph_path = os.path.join(self.root_path,'codegraph.cg')
        if os.path.exists(codegraph_path):
            self.load_from_file(codegraph_path)
            self.statusBar().showMessage('Auto-loaded: codegraph.cg')
        else:
            # No file found, prompt for root path
            self.statusBar().showMessage('No codegraph.cg found')
    
    def prompt_root_path(self):
        """Prompt for root path"""
        if not self.root_path:
            root_path = QFileDialog.getExistingDirectory(
                self, 'Select Project Root Directory', os.getcwd()
            )
            
            if root_path:
                self.root_path = root_path
            else:
                self.root_path = os.getcwd()
        
        self.load_directory("root")
    
    def create_sidebar(self):
        """Create sidebar"""
        sidebar = QWidget()
        layout = QVBoxLayout()
        
        title = QLabel("<b>Subdirs & Classes</b>")
        layout.addWidget(title)
        
        self.root_path_label = QLabel("Root: Not set")
        self.root_path_label.setWordWrap(True)
        self.root_path_label.setStyleSheet("color: #666; font-size: 10px;")
        layout.addWidget(self.root_path_label)
        
        self.subdir_list = QListWidget()
        self.subdir_list.itemDoubleClicked.connect(self.on_subdir_double_click)
        layout.addWidget(self.subdir_list)
        
        add_subdir_btn = QPushButton("+ Add Subdirectory")
        add_subdir_btn.clicked.connect(self.add_subdirectory)
        layout.addWidget(add_subdir_btn)
        
        add_class_btn = QPushButton("+ Add Class")
        add_class_btn.clicked.connect(self.add_class_block)
        layout.addWidget(add_class_btn)
        
        change_root_btn = QPushButton("📁 Change Root Path")
        change_root_btn.clicked.connect(self.change_root_path)
        layout.addWidget(change_root_btn)
        
        refresh_btn = QPushButton("🔄 Refresh")
        refresh_btn.clicked.connect(self.refresh_subdirectories)
        layout.addWidget(refresh_btn)
        
        sidebar.setLayout(layout)
        sidebar.setMaximumWidth(250)
        
        return sidebar
    
    def change_root_path(self):
        """Change root path"""
        root_path = QFileDialog.getExistingDirectory(
            self, 'Select Project Root Directory', self.root_path or os.getcwd()
        )
        
        if root_path:
            self.root_path = root_path
            self.root_path_label.setText(f"Root: {self.root_path}")
            self.statusBar().showMessage(f'Root path: {self.root_path}')
    
    def create_menu_bar(self):
        """Create menu bar"""
        menubar = self.menuBar()
        
        # File menu
        file_menu = menubar.addMenu('File')
        
        open_action = file_menu.addAction('Open codegraph.cg')
        open_action.triggered.connect(self.open_file)
        
        save_action = file_menu.addAction('Save')
        save_action.setShortcut('Ctrl+S')
        save_action.triggered.connect(self.save_file)
        
        save_as_action = file_menu.addAction('Save As...')
        save_as_action.triggered.connect(self.save_file_as)
        
        file_menu.addSeparator()
        
        exit_action = file_menu.addAction('Exit')
        exit_action.triggered.connect(self.close)
        
        # Edit menu
        edit_menu = menubar.addMenu('Edit')
        
        # Undo/Redo actions
        undo_action = self.undo_stack.createUndoAction(self, "Undo")
        undo_action.setShortcut(QKeySequence.Undo)
        edit_menu.addAction(undo_action)
        
        redo_action = self.undo_stack.createRedoAction(self, "Redo")
        redo_action.setShortcut(QKeySequence.Redo)
        edit_menu.addAction(redo_action)
        
        edit_menu.addSeparator()
        
        add_function_action = edit_menu.addAction('Add Function Block')
        add_function_action.setShortcut('Ctrl+F')
        add_function_action.triggered.connect(self.add_function_block)
        
        add_class_action = edit_menu.addAction('Add Class Block')
        add_class_action.setShortcut('Ctrl+Shift+C')
        add_class_action.triggered.connect(self.add_class_block)
        
        add_subdir_action = edit_menu.addAction('Add Subdirectory Block')
        add_subdir_action.setShortcut('Ctrl+D')
        add_subdir_action.triggered.connect(self.add_subdirectory_block)

        add_method_action = edit_menu.addAction('Add Method Block')
        add_method_action.setShortcut('Ctrl+M')
        add_method_action.triggered.connect(self.add_method_block)

        add_other_action = edit_menu.addAction('Add Other Block')
        add_other_action.setShortcut('Ctrl+O')
        add_other_action.triggered.connect(self.add_other_block)

        add_image_action = edit_menu.addAction('Add Image Block')
        add_image_action.triggered.connect(self.add_image_block)

        edit_menu.addSeparator()
        
        rename_action = edit_menu.addAction('Rename Selected (Alias)')
        rename_action.setShortcut('F2')
        rename_action.triggered.connect(self.rename_selected)

        info_action = edit_menu.addAction('Show Info')
        info_action.setShortcut('Ctrl+I')
        info_action.triggered.connect(self.show_block_info_selected)

        edit_menu.addSeparator()
        
        delete_action = edit_menu.addAction('Delete Selected')
        delete_action.setShortcut('Delete')
        delete_action.triggered.connect(self.delete_selected)
        
        # Preferences menu
        pref_menu = menubar.addMenu('Preferences')
        
        theme_menu = pref_menu.addMenu('Theme')
        
        light_action = QAction('☀️ Light', self)
        light_action.setCheckable(True)
        light_action.triggered.connect(lambda: self.set_theme('light'))
        
        dark_action = QAction('🌙 Dark', self)
        dark_action.setCheckable(True)
        dark_action.triggered.connect(lambda: self.set_theme('dark'))
        
        # Set current theme as checked
        if self.current_theme == 'light':
            light_action.setChecked(True)
        else:
            dark_action.setChecked(True)
        
        # Create action group for exclusive selection
        theme_group = QActionGroup(self)
        theme_group.addAction(light_action)
        theme_group.addAction(dark_action)
        theme_group.setExclusive(True)
        
        theme_menu.addAction(light_action)
        theme_menu.addAction(dark_action)
    
    def set_theme(self, theme):
        """Set application theme"""
        self.current_theme = theme
        self.settings.setValue('theme', theme)
        self.apply_theme(theme)
        self.statusBar().showMessage(f'Theme changed to: {theme.capitalize()}')
    
    def apply_theme(self, theme):
        """Apply theme colors to the application"""
        app = QApplication.instance()
        
        if theme == 'dark':
            # Dark theme
            dark_palette = QPalette()
            dark_palette.setColor(QPalette.Window, QColor(53, 53, 53))
            dark_palette.setColor(QPalette.WindowText, Qt.white)
            dark_palette.setColor(QPalette.Base, QColor(35, 35, 35))
            dark_palette.setColor(QPalette.AlternateBase, QColor(53, 53, 53))
            dark_palette.setColor(QPalette.ToolTipBase, QColor(25, 25, 25))
            dark_palette.setColor(QPalette.ToolTipText, Qt.white)
            dark_palette.setColor(QPalette.Text, Qt.white)
            dark_palette.setColor(QPalette.Button, QColor(53, 53, 53))
            dark_palette.setColor(QPalette.ButtonText, Qt.white)
            dark_palette.setColor(QPalette.BrightText, Qt.red)
            dark_palette.setColor(QPalette.Link, QColor(42, 130, 218))
            dark_palette.setColor(QPalette.Highlight, QColor(42, 130, 218))
            dark_palette.setColor(QPalette.HighlightedText, Qt.black)
            
            app.setPalette(dark_palette)
            
            # Dark stylesheet
            app.setStyleSheet("""
                QToolTip { 
                    color: #ffffff; 
                    background-color: #2a2a2a; 
                    border: 1px solid #555;
                }
                QMenu {
                    background-color: #353535;
                    color: #ffffff;
                }
                QMenu::item:selected {
                    background-color: #2a82da;
                }
            """)
        else:
            # Light theme
            light_palette = QPalette()
            light_palette.setColor(QPalette.Window, QColor(240, 240, 240))
            light_palette.setColor(QPalette.WindowText, Qt.black)
            light_palette.setColor(QPalette.Base, QColor(255, 255, 255))
            light_palette.setColor(QPalette.AlternateBase, QColor(245, 245, 245))
            light_palette.setColor(QPalette.ToolTipBase, QColor(255, 255, 220))
            light_palette.setColor(QPalette.ToolTipText, Qt.black)
            light_palette.setColor(QPalette.Text, Qt.black)
            light_palette.setColor(QPalette.Button, QColor(240, 240, 240))
            light_palette.setColor(QPalette.ButtonText, Qt.black)
            light_palette.setColor(QPalette.BrightText, Qt.red)
            light_palette.setColor(QPalette.Link, QColor(0, 100, 200))
            light_palette.setColor(QPalette.Highlight, QColor(0, 120, 215))
            light_palette.setColor(QPalette.HighlightedText, Qt.white)
            
            app.setPalette(light_palette)
            
            # Light stylesheet
            app.setStyleSheet("""
                QToolTip { 
                    color: #000000; 
                    background-color: #ffffdc; 
                    border: 1px solid #999;
                }
            """)
        
        # Update all views
        for tab in self.directory_tabs.values():
            if hasattr(tab, 'view'):
                tab.view.update_theme()
    
    def rename_selected(self):
        """Rename selected block"""
        current_tab = self.directory_tabs.get(self.current_directory)
        if not current_tab:
            return
        
        selected_items = current_tab.scene.selectedItems()
        
        for item in selected_items:
            if isinstance(item, CodeBlock):
                old_name = item.display_name
                
                alias, ok = QInputDialog.getText(
                    self, 
                    'Rename Block (Alias)', 
                    f'Original: {item.name}\n\nEnter display name:',
                    text=old_name
                )
                
                if ok and alias != old_name:
                    command = RenameBlockCommand(item, old_name, alias, f"Rename to '{alias}'")
                    self.undo_stack.push(command)
                break
    
    def get_current_search_path(self):
        """Get search path"""
        if not self.root_path:
            return None
        
        if self.current_directory == "root":
            return self.root_path
        
        relative_path = self.current_directory.replace("root", "", 1).lstrip("/")
        
        if relative_path:
            return os.path.join(self.root_path, relative_path)
        else:
            return self.root_path
    
    def search_function_in_directory(self, function_name, search_path):
        """Search for function definitions and imports"""
        results = []

        if not os.path.exists(search_path):
            return results

        for filename in os.listdir(search_path):
            if not filename.endswith('.py'):
                continue

            file_path = os.path.join(search_path, filename)

            try:
                with open(file_path, 'r', encoding='utf-8') as f:
                    content = f.read()
                    tree = ast.parse(content)
                    lines = content.split('\n')

                    # Search for function definitions
                    for node in ast.walk(tree):
                        if isinstance(node, (ast.FunctionDef, ast.AsyncFunctionDef)):
                            if node.name == function_name:
                                start_line = node.lineno - 1
                                end_line = min(start_line + 10, len(lines))
                                code_snippet = '\n'.join(lines[start_line:end_line])

                                rel_path = os.path.relpath(file_path, self.root_path)

                                results.append({
                                    'file': rel_path,
                                    'line': node.lineno,
                                    'full_path': file_path,
                                    'code': code_snippet,
                                    'type': 'definition'
                                })

                    # Search for imports
                    for node in ast.walk(tree):
                        # Handle: from module import function_name
                        if isinstance(node, ast.ImportFrom):
                            for alias in node.names:
                                imported_name = alias.name
                                alias_name = alias.asname if alias.asname else alias.name

                                if imported_name == function_name or alias_name == function_name:
                                    line_num = node.lineno
                                    code_snippet = lines[line_num - 1] if line_num <= len(lines) else ''
                                    rel_path = os.path.relpath(file_path, self.root_path)

                                    results.append({
                                        'file': rel_path,
                                        'line': line_num,
                                        'full_path': file_path,
                                        'code': code_snippet,
                                        'type': 'import'
                                    })

                        # Handle: import module (where module might contain the function)
                        # This is less common for functions, but included for completeness
                        elif isinstance(node, ast.Import):
                            for alias in node.names:
                                # Check if function_name might be part of module name
                                if function_name in alias.name:
                                    line_num = node.lineno
                                    code_snippet = lines[line_num - 1] if line_num <= len(lines) else ''
                                    rel_path = os.path.relpath(file_path, self.root_path)

                                    results.append({
                                        'file': rel_path,
                                        'line': line_num,
                                        'full_path': file_path,
                                        'code': code_snippet,
                                        'type': 'import'
                                    })

            except Exception as e:
                print(f"Error: {e}")
                continue

        return results

    def search_class_in_directory(self, class_name, search_path):
        """Search for class definitions and imports"""
        results = []

        if not os.path.exists(search_path):
            return results

        for filename in os.listdir(search_path):
            if not filename.endswith('.py'):
                continue

            file_path = os.path.join(search_path, filename)

            try:
                with open(file_path, 'r', encoding='utf-8') as f:
                    content = f.read()
                    tree = ast.parse(content)
                    lines = content.split('\n')

                    # Search for class definitions
                    for node in ast.walk(tree):
                        if isinstance(node, ast.ClassDef):
                            if node.name == class_name:
                                start_line = node.lineno - 1
                                end_line = min(start_line + 10, len(lines))
                                code_snippet = '\n'.join(lines[start_line:end_line])

                                rel_path = os.path.relpath(file_path, self.root_path)

                                results.append({
                                    'file': rel_path,
                                    'line': node.lineno,
                                    'full_path': file_path,
                                    'code': code_snippet,
                                    'type': 'definition'
                                })

                    # Search for imports
                    for node in ast.walk(tree):
                        # Handle: from module import ClassName
                        if isinstance(node, ast.ImportFrom):
                            for alias in node.names:
                                imported_name = alias.name
                                alias_name = alias.asname if alias.asname else alias.name

                                if imported_name == class_name or alias_name == class_name:
                                    line_num = node.lineno
                                    code_snippet = lines[line_num - 1] if line_num <= len(lines) else ''
                                    rel_path = os.path.relpath(file_path, self.root_path)

                                    results.append({
                                        'file': rel_path,
                                        'line': line_num,
                                        'full_path': file_path,
                                        'code': code_snippet,
                                        'type': 'import'
                                    })

                        # Handle: import module (where module might be the class/module name)
                        elif isinstance(node, ast.Import):
                            for alias in node.names:
                                module_name = alias.name
                                alias_name = alias.asname if alias.asname else alias.name

                                # Check if class_name matches module or alias
                                if class_name in module_name or class_name == alias_name:
                                    line_num = node.lineno
                                    code_snippet = lines[line_num - 1] if line_num <= len(lines) else ''
                                    rel_path = os.path.relpath(file_path, self.root_path)

                                    results.append({
                                        'file': rel_path,
                                        'line': line_num,
                                        'full_path': file_path,
                                        'code': code_snippet,
                                        'type': 'import'
                                    })

            except Exception as e:
                print(f"Error: {e}")
                continue

        return results
    
    def check_function_exists(self, block):
        """Check if a function block exists in filesystem"""
        if block.block_type != 'FUNCTION':
            return True
        
        if 'functionName' not in block.metadata:
            return False
        
        function_name = block.metadata.get('functionName')

        search_path = self.get_current_search_path()
        
        if not search_path:
            return False
        
        results = self.search_function_in_directory(function_name, search_path)
        exists = len(results) > 0
        return exists,results

    def check_method_exists(self, block):
        """Check if a function block exists in filesystem"""
        if block.block_type != 'METHOD':
            return True
        
        if 'methodName' not in block.metadata:
            return False
        
        function_name = block.metadata.get('methodName')

        search_path = os.path.dirname(self.get_current_search_path())
        
        if not search_path:
            return False
        
        results = self.search_function_in_directory(function_name, search_path)
        exists = len(results) > 0
        return exists,results

    
    def check_class_exists(self, block):
        """Check if a class block exists in filesystem"""
        if block.block_type != 'CLASS':
            return True
        
        if 'className' not in block.metadata:
            return False
        
        class_name = block.metadata.get('className')
        search_path = self.get_current_search_path()
        
        if not search_path:
            return False
        
        results = self.search_class_in_directory(class_name, search_path)
        exists = len(results) > 0
        return exists,results
    
    def check_subdirectory_exists(self, block):
        """Check if a subdirectory block exists in filesystem"""
        if block.block_type != 'SUBDIRECTORY':
            return True
        
        search_path = self.get_current_search_path()
        
        if not search_path:
            return False
        
        subdir_full_path = os.path.join(search_path, block.name)
        return os.path.exists(subdir_full_path) and os.path.isdir(subdir_full_path)
    
    def validate_all_blocks(self):
        """Validate all blocks in current directory and update their existence status"""
        if not self.root_path:
            QMessageBox.warning(self, "No Root Path", "Please set a root path first!")
            return
        
        current_tab = self.directory_tabs.get(self.current_directory)
        if not current_tab:
            return
        
        validated_count = 0
        missing_count = 0
        
        for block in current_tab.blocks:
            if block.block_type == 'FUNCTION':
                exists,metadata = self.check_function_exists(block)
                if exists and len(metadata) == 1:
                    block.metadata['lineNumber'] = metadata[0].get('line')
                elif not exists:
                    block.metadata['lineNumber'] = None
            elif block.block_type == 'METHOD':
                exists,metadata = self.check_method_exists(block)
                if exists and len(metadata) == 1:
                    block.metadata['lineNumber'] = metadata[0].get('line')
                elif not exists:
                    block.metadata['lineNumber'] = None
            elif block.block_type == 'CLASS':
                exists,metadata = self.check_class_exists(block)
                if exists and len(metadata) == 1:
                    block.metadata['lineNumber'] = metadata[0].get('line')
                elif not exists:
                    block.metadata['lineNumber'] = None
            elif block.block_type == 'SUBDIRECTORY':
                exists = self.check_subdirectory_exists(block)
            elif block.block_type == 'OTHER':
                exists = True  # Other blocks always exist
            else:
                exists = True
            
            block.set_exists(exists)
            validated_count += 1
            
            if not exists:
                missing_count += 1
        
        if missing_count > 0:
            self.statusBar().showMessage(
                f'Validated {validated_count} blocks - {missing_count} missing (red border)'
            )
        else:
            self.statusBar().showMessage(
                f'✓ All {validated_count} blocks exist in filesystem'
            )
    
    def add_function_from_context(self):
        """Add function from context menu"""
        current_tab = self.directory_tabs.get(self.current_directory)
        if not current_tab:
            return
        
        pos = current_tab.view.last_context_pos or QPointF(150, 150)
        self.add_function_block(pos.x(), pos.y())

    def add_method_from_context(self):
        """Add add_method_from_context from context menu"""
        current_tab = self.directory_tabs.get(self.current_directory)
        if not current_tab:
            return
        
        pos = current_tab.view.last_context_pos or QPointF(150, 150)
        self.add_method_block(pos.x(), pos.y())

    def add_class_from_context(self):
        """Add class from context menu"""
        current_tab = self.directory_tabs.get(self.current_directory)
        if not current_tab:
            return
        
        pos = current_tab.view.last_context_pos or QPointF(300, 150)
        self.add_class_block(pos.x(), pos.y())
    
    def add_subdirectory_from_context(self):
        """Add subdirectory from context menu"""
        current_tab = self.directory_tabs.get(self.current_directory)
        if not current_tab:
            return
        
        pos = current_tab.view.last_context_pos or QPointF(400, 150)
        self.add_subdirectory_block(pos.x(), pos.y())
    
    def add_function_block(self, x=None, y=None):
        """Add function block - always creates, marks as non-existent if not found"""
        if not self.root_path:
            QMessageBox.warning(self, "No Root Path", "Please set a root path first!")
            return
        
        name, ok = QInputDialog.getText(self, 'Add Function', 'Function name:')
        
        if not ok or not name:
            return
        
        search_path = self.get_current_search_path()
        self.statusBar().showMessage(f'Searching for "{name}"...')
        
        results = self.search_function_in_directory(name, search_path)
        
        current_tab = self.directory_tabs.get(self.current_directory)
        if not current_tab:
            return
        
        block_id = f"func_{uuid.uuid4().hex}"
        
        if x is None or y is None:
            x = 150
            y = 150 + len(current_tab.blocks) * 100
        
        # Determine if function exists
        exists = len(results) > 0
        selected_result = None
        
        if exists:
            if len(results) == 1:
                selected_result = results[0]
            else:
                dialog = FunctionSearchDialog(name, results, self)
                if dialog.exec_() == QDialog.Accepted:
                    selected_result = dialog.selected_result
        
        # Create block data
        block_data = {
            'id': block_id,
            'type': 'FUNCTION',
            'name': f"{name}()",
            'x': x,
            'y': y,
            'width': 200,
            'height': 80,
            'metadata': {
                'functionName': name
            },
            'style': {
                'color': (None,None,None),
                'border': (None,None,None,None),
                'alpha': None,
                'dashed': None,
            },
            'exists': exists
        }
        
        # Add file path and line number if found
        if selected_result:
            block_data['metadata']['filePath'] = selected_result['file']
            block_data['metadata']['lineNumber'] = selected_result['line']
        
        # Use command for undo/redo
        command = AddBlockCommand(current_tab, block_data, self, f"Add Function '{name}'")
        self.undo_stack.push(command)
        
        if exists:
            self.statusBar().showMessage(f'✓ Added: {name}')
        else:
            self.statusBar().showMessage(f'⚠ Added: {name} (not found - red border)')

    def add_other_from_context(self):
        """Add other block from context menu"""
        current_tab = self.directory_tabs.get(self.current_directory)
        if not current_tab:
            return
        
        pos = current_tab.view.last_context_pos or QPointF(150, 150)
        self.add_other_block(pos.x(), pos.y())

    def add_other_block(self, x=None, y=None):
        """Add other block - simple visualization block with no code link"""
        name, ok = QInputDialog.getText(self, 'Add Other Block', 'Block name:')
        
        if not ok or not name:
            return
        
        current_tab = self.directory_tabs.get(self.current_directory)
        if not current_tab:
            return
        
        block_id = f"other_{uuid.uuid4().hex}"
        
        if x is None or y is None:
            x = 150
            y = 150 + len(current_tab.blocks) * 100
        
        block_data = {
            'id': block_id,
            'type': 'OTHER',
            'name': name,
            'x': x,
            'y': y,
            'width': 200,
            'height': 80,
            'style': {
                'color': (None,None,None),
                'border': (None,None,None,None),
                'alpha': None,
                'dashed': None,
            },
            'metadata': {},
            'exists': True  # Always exists (no validation needed)
        }
        
        # Use command for undo/redo
        command = AddBlockCommand(current_tab, block_data, self, f"Add Other '{name}'")
        self.undo_stack.push(command)
        
        self.statusBar().showMessage(f'✓ Added: {name}')

    def add_image_from_context(self):
        """Add other block from context menu"""
        current_tab = self.directory_tabs.get(self.current_directory)
        if not current_tab:
            return
        
        pos = current_tab.view.last_context_pos or QPointF(150, 150)
        self.add_image_block(pos.x(), pos.y())


    def add_image_block(self, x=None, y=None):
        """Add image block with icon picker dialog"""
        # Open custom image picker dialog
        dialog = ImagePickerDialog(icons_folder='icons', parent=self)
        
        if dialog.exec_() != QDialog.Accepted:
            return
        
        path = dialog.get_selected_path()
        
        if not path:
            return
        
        current_tab = self.directory_tabs.get(self.current_directory)
        if not current_tab:
            return
        
        block_id = f"image_{uuid.uuid4().hex[:8]}"  # Shorter ID
        
        if x is None or y is None:
            x = 150
            y = 150 + len(current_tab.blocks) * 100
        
        # Extract filename for display name
        filename = os.path.basename(path)
        
        block_data = {
            'id': block_id,
            'type': 'IMAGE',
            'name': filename,  # Use filename as name
            'x': x,
            'y': y,
            'width': 300,  # Larger default for images
            'height': 300,
            'style': {
                'color': (None,None,None),
                'border': (None,None,None,None),
                'alpha': None,
                'dashed': None,
            },
            'metadata': {'image_path': path},
            'exists': True
        }
        
        # Use command for undo/redo
        command = AddBlockCommand(current_tab, block_data, self, f"Add Image '{filename}'")
        self.undo_stack.push(command)
        
        self.statusBar().showMessage(f'✓ Added image: {filename}')


    def add_class_block(self, x=None, y=None):
        """Add class block - always creates, marks as non-existent if not found"""
        if not self.root_path:
            QMessageBox.warning(self, "No Root Path", "Please set a root path first!")
            return
        
        name, ok = QInputDialog.getText(self, 'Add Class', 'Class name:')
        
        if not ok or not name:
            return
        
        search_path = self.get_current_search_path()
        self.statusBar().showMessage(f'Searching for class "{name}"...')
        
        results = self.search_class_in_directory(name, search_path)
        
        current_tab = self.directory_tabs.get(self.current_directory)
        if not current_tab:
            return
        
        block_id = f"class_{uuid.uuid4().hex}"
        
        if x is None or y is None:
            x = 300
            y = 150 + len(current_tab.blocks) * 100
        
        # Determine if class exists
        exists = len(results) > 0
        selected_result = None
        
        if exists:
            if len(results) == 1:
                selected_result = results[0]
            else:
                dialog = FunctionSearchDialog(name, results, self)
                if dialog.exec_() == QDialog.Accepted:
                    selected_result = dialog.selected_result
        
        # Create block data
        block_data = {
            'id': block_id,
            'type': 'CLASS',
            'name': name,
            'x': x,
            'y': y,
            'width': 250,
            'height': 100,
            'style': {
                'color': (None,None,None),
                'border': (None,None,None,None),
                'alpha': None,
                'dashed': None,
            },
            'metadata': {
                'className': name
            },
            'exists': exists
        }
        
        # Add file path and line number if found
        if selected_result:
            block_data['metadata']['filePath'] = selected_result['file']
            block_data['metadata']['lineNumber'] = selected_result['line']
        
        # Use command for undo/redo
        command = AddBlockCommand(current_tab, block_data, self, f"Add Class '{name}'")
        self.undo_stack.push(command)
        
        # Create directory data for class (like subdirectory)
        class_path = f"{self.current_directory}/{name}"
        if class_path not in self.directory_data:
            self.directory_data[class_path] = {'blocks': [], 'connections': []}
        
        self.refresh_subdirectories()
        
        if exists:
            self.statusBar().showMessage(f'✓ Added: {name}')
        else:
            self.statusBar().showMessage(f'⚠ Added: {name} (not found - red border)')

    def add_method_block(self, x=None, y=None):
        """Add method block - always creates, marks as non-existent if not found"""
        if not self.root_path:
            QMessageBox.warning(self, "No Root Path", "Please set a root path first!")
            return
        
        name, ok = QInputDialog.getText(self, 'Add Method', 'Method name:')
        
        if not ok or not name:
            return
        
        search_path = os.path.dirname(self.get_current_search_path())
        self.statusBar().showMessage(f'Searching for "{name}"...')
        
        results = self.search_function_in_directory(name, search_path)
        
        current_tab = self.directory_tabs.get(self.current_directory)
        if not current_tab:
            return
        
        block_id = f"mthd_{uuid.uuid4().hex}"
        
        if x is None or y is None:
            x = 150
            y = 150 + len(current_tab.blocks) * 100
        
        # Determine if function exists
        exists = len(results) > 0
        selected_result = None
        
        if exists:
            if len(results) == 1:
                selected_result = results[0]
            else:
                dialog = FunctionSearchDialog(name, results, self)
                if dialog.exec_() == QDialog.Accepted:
                    selected_result = dialog.selected_result
        
        # Create block data
        block_data = {
            'id': block_id,
            'type': 'METHOD',
            'name': f"{name}()",
            'x': x,
            'y': y,
            'width': 200,
            'height': 80,
            'style': {
                'color': (None,None,None),
                'border': (None,None,None,None),
                'alpha': None,
                'dashed': None,
            },
            'metadata': {
                'methodName': name
            },
            'exists': exists
        }
        
        # Add file path and line number if found
        if selected_result:
            block_data['metadata']['filePath'] = selected_result['file']
            block_data['metadata']['lineNumber'] = selected_result['line']
        
        # Use command for undo/redo
        command = AddBlockCommand(current_tab, block_data, self, f"Add Function '{name}'")
        self.undo_stack.push(command)
        
        if exists:
            self.statusBar().showMessage(f'✓ Added: {name}')
        else:
            self.statusBar().showMessage(f'⚠ Added: {name} (not found - red border)')

    def add_subdirectory_block(self, x=None, y=None):
        """Add subdirectory block - always creates, marks as non-existent if not found"""
        if not self.root_path:
            QMessageBox.warning(self, "No Root Path", "Please set a root path first!")
            return
        
        name, ok = QInputDialog.getText(self, 'Add Subdirectory', 'Subdirectory name:')
        
        if not ok or not name:
            return
        
        # Check if subdirectory exists
        search_path = self.get_current_search_path()
        subdir_full_path = os.path.join(search_path, name)
        
        exists = os.path.exists(subdir_full_path) and os.path.isdir(subdir_full_path)
        
        current_tab = self.directory_tabs.get(self.current_directory)
        if not current_tab:
            return
        
        block_id = f"subdir_{uuid.uuid4().hex}"
        
        if x is None or y is None:
            x = 400
            y = 150 + len(current_tab.blocks) * 100
        
        block_data = {
            'id': block_id,
            'type': 'SUBDIRECTORY',
            'name': name,
            'x': x,
            'y': y,
            'width': 250,
            'height': 100,
            'style': {
                'color': (None,None,None),
                'border': (None,None,None,None),
                'alpha': None,
                'dashed': None,
            },
            'metadata': {},
            'exists': exists
        }
        
        # Use command for undo/redo
        command = AddBlockCommand(current_tab, block_data, self, f"Add Subdirectory '{name}'")
        self.undo_stack.push(command)
        
        if exists:
            self.statusBar().showMessage(f'✓ Added: {name}')
        else:
            self.statusBar().showMessage(f'⚠ Added: {name} (not found - red border)')

    def add_group_container(self, name, x, y, width, height):
        """Add a group container block"""
        current_tab = self.directory_tabs.get(self.current_directory)
        if not current_tab:
            return
        
        block_id = f"group_{len(current_tab.blocks) + 1}"
        
        block_data = {
            'id': block_id,
            'type': 'GROUP',
            'name': name,
            'x': x,
            'y': y,
            'width': width,
            'height': height,
            'style': {
                'color': (None,None,None),
                'border': (None,None,None,None),
                'alpha': None,
                'dashed': None,
            },
            'metadata': {
                'isGroup': True
            },
            'exists': True
        }
        
        # Use command for undo/redo
        command = AddBlockCommand(current_tab, block_data, self, f"Add Group '{name}'")
        self.undo_stack.push(command)
        
        self.statusBar().showMessage(f'✓ Created group: {name}')
        
    def load_directory(self, directory_path):
        """Load directory"""
        self.current_directory = directory_path
        
        # Clear undo stack when switching directories
        self.undo_stack.clear()
        
        for i in reversed(range(self.main_layout.count())): 
            self.main_layout.itemAt(i).widget().setParent(None)
        
        if directory_path not in self.directory_tabs:
            parent_callback = self.go_to_parent if directory_path != "root" else None
            tab = DirectoryTab(directory_path, self, parent_callback)
            self.directory_tabs[directory_path] = tab
            
            if directory_path in self.directory_data:
                self.load_directory_data(tab, self.directory_data[directory_path])
        
        tab = self.directory_tabs[directory_path]
        self.main_layout.addWidget(tab)
        
        self.refresh_subdirectories()
        
        if self.root_path:
            self.root_path_label.setText(f"Root: {self.root_path}")
        
        self.statusBar().showMessage(f'Viewing: {directory_path}')
    
    def load_directory_data(self, tab, data):
        """Load directory data"""
        block_map = {}
        
        for block_data in data.get('blocks', []):
            block = tab.add_block(block_data)
            block_map[block_data['id']] = block
            
            if block.block_type == 'SUBDIRECTORY':
                block.mouseDoubleClickEvent = lambda event, b=block: self.open_subdirectory(b)
            elif block.block_type == 'CLASS':
                block.mouseDoubleClickEvent = lambda event, b=block: self.open_class(b)
            elif block.block_type == 'FUNCTION':
                block.mouseDoubleClickEvent = lambda event, b=block: self.open_function(b)
            elif block.block_type == 'METHOD':
                block.mouseDoubleClickEvent = lambda event, b=block: self.open_function(b)
                
        for conn_data in data.get('connections', []):
            from_block = block_map.get(conn_data['from'])
            to_block = block_map.get(conn_data['to'])
            
            if from_block and to_block:
                from_side = conn_data.get('from_side', 'right')
                to_side = conn_data.get('to_side', 'left')
                flow_type = conn_data.get('flow_type', 'one_way')
                line_style = conn_data.get('line_style', 'solid')
                line_color_data = conn_data.get('line_color', {'r': 100, 'g': 100, 'b': 100})
                line_color = QColor(line_color_data['r'], line_color_data['g'], line_color_data['b'])
                tab.add_connection(from_block, to_block, from_side, to_side, flow_type, line_style, line_color)

    def open_subdirectory(self, block):
        """Open subdirectory"""
        subdir_path = f"{self.current_directory}/{block.name}"
        self.load_directory(subdir_path)
    
    def open_class(self, block):
        """Open class (navigate to its methods)"""
        class_path = f"{self.current_directory}/{block.name}"
        self.load_directory(class_path)
    
    def open_function(self, block):
        """Open function in VS Code"""
        if 'filePath' not in block.metadata:
            self.statusBar().showMessage("Cannot open: function location unknown")
            return
        
        file_path = block.metadata.get('filePath', '')
        line_number = block.metadata.get('lineNumber', 1)
        
        full_path = os.path.join(self.root_path, file_path)
        
        if not os.path.exists(full_path):
            self.statusBar().showMessage(f"File not found: {full_path}")
            return
        
        command = f'code --goto "{full_path}:{line_number}"'
        
        try:
            subprocess.Popen(command, shell=True)
            self.statusBar().showMessage(f"Opening {file_path}:{line_number}")
        except Exception as e:
            self.statusBar().showMessage(f"Error: {e}")
    
    def go_to_parent(self):
        """Go to parent directory"""
        if self.current_directory == "root":
            return
        
        self.save_current_directory_data()
        
        parent_path = "/".join(self.current_directory.split("/")[:-1])
        if not parent_path:
            parent_path = "root"
        
        self.load_directory(parent_path)
    
    def refresh_subdirectories(self):
        """Refresh subdirectories and classes"""
        self.subdir_list.clear()
        
        current_tab = self.directory_tabs.get(self.current_directory)
        if not current_tab:
            return
        
        # Get subdirectories
        subdirs = [block for block in current_tab.blocks if block.block_type == 'SUBDIRECTORY']
        for subdir in subdirs:
            item = QListWidgetItem(f"📁 {subdir.name}")
            item.setData(Qt.UserRole, subdir)
            self.subdir_list.addItem(item)
        
        # Get classes
        classes = [block for block in current_tab.blocks if block.block_type == 'CLASS']
        for cls in classes:
            item = QListWidgetItem(f"🟡 {cls.name}")
            item.setData(Qt.UserRole, cls)
            self.subdir_list.addItem(item)
    
    def on_subdir_double_click(self, item):
        """Handle subdir/class double-click"""
        block = item.data(Qt.UserRole)
        if block.block_type == 'SUBDIRECTORY':
            self.open_subdirectory(block)
        elif block.block_type == 'CLASS':
            self.open_class(block)
    
    def add_subdirectory(self):
        """Add subdirectory"""
        self.add_subdirectory_block()
    
    def delete_selected(self):
        """Delete selected items using undo commands"""
        current_tab = self.directory_tabs.get(self.current_directory)
        if not current_tab:
            return
        
        selected_items = current_tab.scene.selectedItems()
        
        if not selected_items:
            return
        
        # Group multiple deletes into one undo action
        self.undo_stack.beginMacro(f"Delete {len(selected_items)} item(s)")
        
        for item in selected_items:
            if isinstance(item, CodeBlock):
                command = DeleteBlockCommand(current_tab, item, self, f"Delete Block '{item.display_name}'")
                self.undo_stack.push(command)
            
            elif isinstance(item, Connection):
                command = DeleteConnectionCommand(current_tab, item, "Delete Connection")
                self.undo_stack.push(command)
        
        self.undo_stack.endMacro()
        
        self.statusBar().showMessage(f'Deleted {len(selected_items)} item(s)')

    def save_current_directory_data(self):
        """Save current directory data"""
        current_tab = self.directory_tabs.get(self.current_directory)
        if current_tab:
            self.directory_data[self.current_directory] = current_tab.get_data()

    def save_all_directory_data(self):
        for directory_path, tab in self.directory_tabs.items():
            self.directory_data[directory_path] = tab.get_data()

    def open_file(self):
        """Open file"""
        file_path, _ = QFileDialog.getOpenFileName(
            self, 'Open CodeGraph', self.root_path, 'CodeGraph Files (*.cg);;All Files (*)'
        )
        
        if file_path:
            self.load_from_file(file_path)
    
    def load_from_file(self, file_path):
        """Load from file"""
        try:
            with open(file_path, 'r', encoding='utf-8') as f:
                data = json.load(f)
            
            if '_root_path' in data:
                self.root_path = data['_root_path']
                del data['_root_path']
            
            self.directory_data = data
            self.directory_tabs.clear()
            
            self.current_directory = "root"
            self.load_directory("root")
            
            self.current_file = file_path
            self.statusBar().showMessage(f'Loaded: {file_path}')
            
        except Exception as e:
            self.statusBar().showMessage(f'Error: {e}')
            QMessageBox.critical(self, "Error", f"Failed to load:\n{e}")
    
    def save_file(self):
        """Save file"""
        try:
            self.validate_all_blocks()
        except Exception as e:
            pass
        if self.current_file:
            self.save_to_file(self.current_file)
        else:
            self.save_file_as()
    
    def save_file_as(self):
        """Save as"""
        try:
            self.validate_all_blocks()
        except Exception as e:
            pass
        file_path, _ = QFileDialog.getSaveFileName(
            self, 
            'Save CodeGraph', 
            os.path.join(self.root_path, 'codegraph.cg'),  # Default path with filename
            'CodeGraph Files (*.cg);;All Files (*)'
        )

        if file_path:
            self.save_to_file(file_path)
    
    def save_to_file(self, file_path):
        """Save to file"""
        try:
            self.validate_all_blocks()
        except Exception as e:
            pass
        try:
            self.save_all_directory_data()
            
            save_data = dict(self.directory_data)
            save_data['_root_path'] = self.root_path
            
            with open(file_path, 'w', encoding='utf-8') as f:
                json.dump(save_data, f, indent=2)
            
            self.current_file = file_path
            self.statusBar().showMessage(f'Saved: {file_path}')
            
        except Exception as e:
            self.statusBar().showMessage(f'Error: {e}')
            QMessageBox.critical(self, "Error", f"Failed to save:\n{e}")

    def show_block_info_selected(self):
        """Show info for selected block (keyboard shortcut)"""
        current_tab = self.directory_tabs.get(self.current_directory)
        if not current_tab:
            return
        
        selected_items = current_tab.scene.selectedItems()
        
        for item in selected_items:
            if isinstance(item, CodeBlock):
                self.show_block_info(item)
                break
    
    def show_block_info(self, block):
        """Show info dialog for a block"""
        dialog = InfoDialog(block, self)
        
        # Extract docstring for functions and classes
        if block.block_type in ['FUNCTION', 'CLASS','METHOD']:
            docstring = self.extract_docstring(block)
            dialog.set_docstring(docstring)
        
        dialog.exec_()
    
    def extract_docstring(self, block):
        """Extract docstring from function or class, including imported symbols"""
        if 'filePath' not in block.metadata:
            return None
        
        file_path = block.metadata.get('filePath', '')
        full_path = os.path.join(self.root_path, file_path)
        
        if not os.path.exists(full_path):
            return None
        
        try:
            with open(full_path, 'r', encoding='utf-8') as f:
                content = f.read()
                tree = ast.parse(content)
                
                target_name = block.metadata.get('functionName') or block.metadata.get('className')
                
                # First, try to find the definition in the current file
                for node in ast.walk(tree):
                    if block.block_type in ('FUNCTION', 'METHOD'):
                        if isinstance(node, (ast.FunctionDef, ast.AsyncFunctionDef)):
                            if node.name == target_name:
                                return ast.get_docstring(node)
                    elif block.block_type == 'CLASS':
                        if isinstance(node, ast.ClassDef):
                            if node.name == target_name:
                                return ast.get_docstring(node)
                
                # If not found, check if it's imported and resolve the import
                docstring = self._resolve_imported_docstring(tree, target_name, block.block_type, full_path)
                if docstring:
                    return docstring
        
        except Exception as e:
            print(f"Error extracting docstring: {e}")
            return None
        
        return None
    
    def _resolve_imported_docstring(self, tree, target_name, block_type, current_file_path):
        """Resolve imports and extract docstring from the original definition"""
        import_info = None
        
        # Search for import statements
        for node in ast.walk(tree):
            # Handle: from module import target_name
            if isinstance(node, ast.ImportFrom):
                for alias in node.names:
                    imported_name = alias.name
                    alias_name = alias.asname if alias.asname else alias.name
                    
                    if alias_name == target_name:
                        # Found the import
                        import_info = {
                            'module': node.module,
                            'name': imported_name,
                            'level': node.level  # For relative imports
                        }
                        break
            
            # Handle: import module (less common but possible)
            elif isinstance(node, ast.Import):
                for alias in node.names:
                    module_name = alias.name
                    alias_name = alias.asname if alias.asname else alias.name
                    
                    if alias_name == target_name or target_name in module_name:
                        import_info = {
                            'module': module_name,
                            'name': target_name,
                            'level': 0
                        }
                        break
            
            if import_info:
                break
        
        if not import_info:
            return None
        
        # Resolve the module path to a file
        try:
            resolved_path = self._resolve_module_path(
                import_info['module'], 
                import_info['level'], 
                current_file_path
            )
            
            if not resolved_path or not os.path.exists(resolved_path):
                return None
            
            # Parse the resolved file and extract docstring
            with open(resolved_path, 'r', encoding='utf-8') as f:
                content = f.read()
                import_tree = ast.parse(content)
                
                for node in ast.walk(import_tree):
                    if block_type in ('FUNCTION', 'METHOD'):
                        if isinstance(node, (ast.FunctionDef, ast.AsyncFunctionDef)):
                            if node.name == import_info['name']:
                                return ast.get_docstring(node)
                    elif block_type == 'CLASS':
                        if isinstance(node, ast.ClassDef):
                            if node.name == import_info['name']:
                                return ast.get_docstring(node)
        
        except Exception as e:
            print(f"Error resolving import: {e}")
            return None
        
        return None
    
    def _resolve_module_path(self, module_name, level, current_file_path):
        """Convert module name to file path"""
        if not module_name:
            return None
        
        # Get the directory of the current file
        current_dir = os.path.dirname(current_file_path)
        
        # Handle relative imports (level > 0 means relative)
        if level > 0:
            # Go up 'level' directories
            for _ in range(level):
                current_dir = os.path.dirname(current_dir)
        else:
            # Absolute import - start from root_path
            current_dir = self.root_path
        
        # Convert module.path.name to module/path/name.py
        module_parts = module_name.split('.')
        module_path = os.path.join(current_dir, *module_parts)
        
        # Try as a .py file first
        if os.path.exists(module_path + '.py'):
            return module_path + '.py'
        
        # Try as a package (__init__.py)
        init_path = os.path.join(module_path, '__init__.py')
        if os.path.exists(init_path):
            return init_path
        
        return None