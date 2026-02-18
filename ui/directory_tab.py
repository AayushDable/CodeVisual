from PyQt5.QtWidgets import (QGraphicsScene, QGraphicsRectItem,
                             QGraphicsTextItem, QWidget, QVBoxLayout, QHBoxLayout,
                             QPushButton, QLabel, QComboBox, QColorDialog, QSplitter,
                             QTextEdit, QFrame)
from PyQt5.QtCore import Qt
from PyQt5.QtGui import QPen, QBrush, QColor, QFont






from graphics.directory_view import DirectoryGraphView
from graphics.connection import Connection
from graphics.code_block import CodeBlock




from commands.graph_commands import AddConnectionCommand,ChangeBlockStyleCommand






class DirectoryTab(QWidget):
    """A tab representing one directory level"""


    _info_panel_collapsed = False


    def __init__(self, directory_path, parent_window, parent_callback=None):
        super().__init__()
        
        self.directory_path = directory_path
        self.parent_window = parent_window
        self.parent_callback = parent_callback
        self.blocks = []
        self.connections = []
        
        self.active_connection_point = None
        
        self.current_flow_type = 'one_way'
        self.current_line_style = 'solid'
        self.current_line_color = QColor(100, 100, 100)  # Default gray
        
        self.init_ui()
    
    def showEvent(self, event):
        """Called when tab becomes visible - sync panel state"""
        super().showEvent(event)
        # Sync the panel state whenever this tab is shown
        self._sync_panel_state()
    
    def _sync_panel_state(self):
        """Synchronize panel visibility and splitter with global state"""
        if DirectoryTab._info_panel_collapsed:
            if self.info_content.isVisible():
                self.info_content.hide()
            self.toggle_panel_btn.setText("▲")
            total = self.splitter.height()
            if total > 0:
                self.splitter.setSizes([total - 25, 25])
        else:
            if not self.info_content.isVisible():
                self.info_content.show()
            self.toggle_panel_btn.setText("▼")
            total = self.splitter.height()
            if total > 0:
                self.splitter.setSizes([total - 120, 120])
    
    def init_ui(self):
        """Initialize the directory tab UI"""
        layout = QVBoxLayout()
        
        # Toolbar
        toolbar_layout = QHBoxLayout()
        
        if self.parent_callback:
            self.parent_btn = QPushButton("↑ Parent")
            self.parent_btn.clicked.connect(self.parent_callback)
            toolbar_layout.addWidget(self.parent_btn)
        
        self.path_label = QLabel(f"<b>{self.directory_path}</b>")
        toolbar_layout.addWidget(self.path_label)
        
        toolbar_layout.addSpacing(20)
        
        flow_label = QLabel("Flow:")
        toolbar_layout.addWidget(flow_label)
        
        self.flow_combo = QComboBox()
        self.flow_combo.addItem("→ One-way", "one_way")
        self.flow_combo.addItem("↔ Bidirectional", "bidirectional")
        self.flow_combo.addItem("— No arrow", "none")
        self.flow_combo.currentIndexChanged.connect(self.on_flow_type_changed)
        toolbar_layout.addWidget(self.flow_combo)
        
        toolbar_layout.addSpacing(10)
        
        line_label = QLabel("Line:")
        toolbar_layout.addWidget(line_label)
        
        self.line_combo = QComboBox()
        self.line_combo.addItem("━ Solid", "solid")
        self.line_combo.addItem("┉ Dashed", "dashed")
        self.line_combo.currentIndexChanged.connect(self.on_line_style_changed)
        toolbar_layout.addWidget(self.line_combo)
        
        toolbar_layout.addSpacing(10)
        
        # Color picker
        color_label = QLabel("Color:")
        toolbar_layout.addWidget(color_label)
        
        self.color_combo = QComboBox()
        self.color_combo.addItem("⚫ Black", QColor(0, 0, 0))
        self.color_combo.addItem("⚪ Gray", QColor(100, 100, 100))
        self.color_combo.addItem("🔴 Red", QColor(220, 53, 69))
        self.color_combo.addItem("🔵 Blue", QColor(0, 123, 255))
        self.color_combo.addItem("🟢 Green", QColor(40, 167, 69))
        self.color_combo.addItem("🟡 Yellow", QColor(255, 193, 7))
        self.color_combo.addItem("🟣 Purple", QColor(111, 66, 193))
        self.color_combo.addItem("🟠 Orange", QColor(253, 126, 20))
        self.color_combo.addItem("🎨 Custom...", None)
        self.color_combo.setCurrentIndex(1)  # Default to Gray
        self.color_combo.currentIndexChanged.connect(self.on_line_color_changed)
        toolbar_layout.addWidget(self.color_combo)
        
        toolbar_layout.addSpacing(20)

        self.add_func_btn = QPushButton("➕ Add Function")
        self.add_func_btn.clicked.connect(self.on_add_function_clicked)
        toolbar_layout.addWidget(self.add_func_btn)

        # Validate button
        validate_btn = QPushButton("🔍 Validate Blocks")
        validate_btn.setToolTip("Check if all blocks exist in filesystem")
        validate_btn.clicked.connect(self.parent_window.validate_all_blocks)
        toolbar_layout.addWidget(validate_btn)
        
        toolbar_layout.addSpacing(10)

        # Toggle connection points button
        self.show_connections = False  # Start with connections hidden
        self.toggle_connections_btn = QPushButton("Show Connections")
        self.toggle_connections_btn.setToolTip("Show/Hide connection points on blocks")
        self.toggle_connections_btn.clicked.connect(self.toggle_connection_points)
        toolbar_layout.addWidget(self.toggle_connections_btn)
        
        toolbar_layout.addSpacing(10)

        zoom_in_btn = QPushButton("🔍+")
        zoom_in_btn.setMaximumWidth(50)
        zoom_in_btn.setToolTip("Zoom In")
        zoom_in_btn.clicked.connect(self.zoom_in)
        toolbar_layout.addWidget(zoom_in_btn)
        
        zoom_out_btn = QPushButton("🔍-")
        zoom_out_btn.setMaximumWidth(50)
        zoom_out_btn.setToolTip("Zoom Out")
        zoom_out_btn.clicked.connect(self.zoom_out)
        toolbar_layout.addWidget(zoom_out_btn)
        
        zoom_reset_btn = QPushButton("⊡")
        zoom_reset_btn.setMaximumWidth(50)
        zoom_reset_btn.setToolTip("Reset Zoom")
        zoom_reset_btn.clicked.connect(self.zoom_reset)
        toolbar_layout.addWidget(zoom_reset_btn)
        
        toolbar_layout.addStretch()
        
        help_label = QLabel("<i>Middle-click to pan | Scroll to zoom</i>")
        help_label.setStyleSheet("color: #666; font-size: 10px;")
        toolbar_layout.addWidget(help_label)
        
        layout.addLayout(toolbar_layout)
        
        # Splitter for canvas and info panel
        self.splitter = QSplitter(Qt.Vertical)
        
        # Canvas area
        self.scene = QGraphicsScene()
        self.scene.setSceneRect(0, 0, 3000, 3000)
        
        self.draw_directory_boundary()
        
        self.view = DirectoryGraphView(self.scene, self.parent_window)
        
        # Connect selection changed to update info panel
        self.scene.selectionChanged.connect(self.on_selection_changed)
        
        self.splitter.addWidget(self.view)
        
        # Info panel
        self.info_panel = self.create_info_panel()
        self.splitter.addWidget(self.info_panel)
        
        # Set initial splitter sizes based on global state
        if DirectoryTab._info_panel_collapsed:
            self.splitter.setSizes([10000, 25])
        else:
            self.splitter.setSizes([800, 120])
        
        layout.addWidget(self.splitter)
        
        self.setLayout(layout)

    def create_info_panel(self):
        """Create the bottom info panel"""
        panel = QWidget()
        panel_layout = QVBoxLayout()
        panel_layout.setContentsMargins(8, 2, 8, 2)
        panel_layout.setSpacing(2)
        
        # Header with toggle button
        header_layout = QHBoxLayout()
        header_layout.setContentsMargins(0, 0, 0, 0)
        
        self.info_title = QLabel("<b>📊 Info</b>")
        self.info_title.setStyleSheet("font-size: 11px;")
        header_layout.addWidget(self.info_title)
        
        header_layout.addStretch()
        
        self.toggle_panel_btn = QPushButton("▼" if not DirectoryTab._info_panel_collapsed else "▲")
        self.toggle_panel_btn.setMaximumWidth(30)
        self.toggle_panel_btn.setMaximumHeight(20)
        self.toggle_panel_btn.setToolTip("Hide/Show Info Panel")
        self.toggle_panel_btn.clicked.connect(self.toggle_info_panel)
        header_layout.addWidget(self.toggle_panel_btn)
        
        panel_layout.addLayout(header_layout)
        
        # Info content area
        self.info_content = QWidget()
        info_content_layout = QVBoxLayout()
        info_content_layout.setContentsMargins(0, 2, 0, 0)
        info_content_layout.setSpacing(1)
        
        # Block name
        self.info_name_label = QLabel("<i>No block selected</i>")
        self.info_name_label.setStyleSheet("font-size: 13px; color: #666;")
        info_content_layout.addWidget(self.info_name_label)
        
        # Block type
        self.info_type_label = QLabel("")
        info_content_layout.addWidget(self.info_type_label)
        
        # File path
        self.info_file_label = QLabel("")
        info_content_layout.addWidget(self.info_file_label)
        
        # Docstring/Description
        self.info_text = QTextEdit()
        self.info_text.setReadOnly(True)
        self.info_text.setMaximumHeight(55)
        self.info_text.setPlaceholderText("Docstring or description will appear here...")
        font = QFont("Courier", 9)
        self.info_text.setFont(font)
        info_content_layout.addWidget(self.info_text)
        
        self.info_content.setLayout(info_content_layout)
        panel_layout.addWidget(self.info_content)
        
        # Set initial visibility based on global state
        if DirectoryTab._info_panel_collapsed:
            self.info_content.hide()
        
        panel.setLayout(panel_layout)
        
        return panel



    def toggle_info_panel(self):
        """Toggle info panel visibility"""
        if self.info_content.isVisible():
            # Collapse
            self.info_content.hide()
            self.toggle_panel_btn.setText("▲")
            DirectoryTab._info_panel_collapsed = True
            total = self.splitter.height()
            self.splitter.setSizes([total - 25, 25])
        else:
            # Expand
            self.info_content.show()
            self.toggle_panel_btn.setText("▼")
            DirectoryTab._info_panel_collapsed = False
            total = self.splitter.height()
            self.splitter.setSizes([total - 120, 120])


    
    def on_selection_changed(self):
        """Handle selection change in scene"""
        selected_items = self.scene.selectedItems()
        
        if not selected_items:
            self.clear_info_panel()
            return
        
        # Get first selected block
        for item in selected_items:
            if isinstance(item, CodeBlock):
                self.update_info_panel(item)
                return
        
        self.clear_info_panel()
    
    def update_info_panel(self, block):
        """Update info panel with block information"""
        # Update name (show alias + original if different)
        if hasattr(block, "name") and block.display_name != block.name:
            # Alias as main, original as subtle hint
            name_html = (
                f"<b style='font-size: 14px;'>{block.display_name}</b>"
                f"<br><span style='font-size: 14px; color: #666;'>"
                f"Original name: {block.name}"
                f"</span>"
            )
        else:
            name_html = f"<b style='font-size: 14px;'>{block.display_name}</b>"

        self.info_name_label.setText(name_html)

        # Update type
        type_icons = {
            'FUNCTION': '⚡',
            'CLASS': '🟡',
            'SUBDIRECTORY': '📁',
            'METHOD': '🟣',
            'IMAGE': '🖼️'
        }
        icon = type_icons.get(block.block_type, '📦')
        self.info_type_label.setText(f"<b>Type:</b> {icon} {block.block_type}")

        # Update file path
        if 'filePath' in block.metadata:
            file_path = block.metadata['filePath']
            line_num = block.metadata.get('lineNumber', '?')
            self.info_file_label.setText(f"<b>File:</b> {file_path}:{line_num}")
            self.info_file_label.show()
        else:
            self.info_file_label.hide()

        # Update docstring/description
        if block.block_type in ['FUNCTION', 'METHOD', 'CLASS']:
            docstring = self.parent_window.extract_docstring(block)
            if docstring:
                self.info_text.setPlainText(docstring)
                self.info_text.setStyleSheet("")
            else:
                self.info_text.setPlainText("No docstring available.")
                self.info_text.setStyleSheet("color: #999; font-style: italic;")
        else:
            # Show description for subdirectories
            description = block.metadata.get('description', '')
            if description:
                self.info_text.setPlainText(description)
                self.info_text.setStyleSheet("")
            else:
                self.info_text.setPlainText("No description. Right-click → Show Info to add one.")
                self.info_text.setStyleSheet("color: #999; font-style: italic;")

    
    def clear_info_panel(self):
        """Clear info panel when nothing is selected"""
        self.info_name_label.setText("<i>No block selected</i>")
        self.info_name_label.setStyleSheet("font-size: 13px; color: #666;")
        self.info_type_label.setText("")
        self.info_file_label.setText("")
        self.info_text.clear()
        self.info_text.setPlaceholderText("Select a block to see its information...")
    
    def zoom_in(self):
        """Zoom in"""
        self.view.scale(1.2, 1.2)
    
    def zoom_out(self):
        """Zoom out"""
        self.view.scale(1/1.2, 1/1.2)
    
    def zoom_reset(self):
        """Reset zoom"""
        self.view.resetTransform()
    
    def on_flow_type_changed(self, index):
        """Handle flow type change"""
        self.current_flow_type = self.flow_combo.itemData(index)
        
        selected_items = self.scene.selectedItems()
        for item in selected_items:
            if isinstance(item, Connection):
                item.set_flow_type(self.current_flow_type)
                self.parent_window.statusBar().showMessage(f'Flow: {self.flow_combo.currentText()}')
    
    def on_line_style_changed(self, index):
        """Handle line style change"""
        self.current_line_style = self.line_combo.itemData(index)
        
        selected_items = self.scene.selectedItems()
        for item in selected_items:
            if isinstance(item, Connection):
                item.set_line_style(self.current_line_style)
                self.parent_window.statusBar().showMessage(f'Line: {self.line_combo.currentText()}')
    
    def on_line_color_changed(self, index):
        """Handle line color change"""
        color_data = self.color_combo.itemData(index)
        
        if color_data is None:
            # Custom color selected - open color picker
            color = QColorDialog.getColor(
                self.current_line_color,
                self,
                "Choose Connection Color"
            )
            
            if color.isValid():
                self.current_line_color = color
                
                selected_items = self.scene.selectedItems()
                applied = False
                for item in selected_items:
                    if isinstance(item, Connection):
                        item.set_line_color(color)
                        applied = True
                    elif isinstance(item, CodeBlock):
                        old_style = {
                            'color': QColor(item.style['color']),
                            'border': QColor(item.style['border']),
                            'alpha': item.style['alpha'],
                            'dashed': item.style['dashed']
                        }
                        new_style = {**old_style, 'color': QColor(color)}
                        cmd = ChangeBlockStyleCommand(item, old_style, new_style, "Change Block Color")
                        self.parent_window.undo_stack.push(cmd)
                        applied = True

                if applied:
                    self.parent_window.statusBar().showMessage(
                        f'Color: Custom RGB({color.red()}, {color.green()}, {color.blue()})'
                    )
            
            # Reset combo to previous color (don't stay on "Custom...")
            self.color_combo.blockSignals(True)
            self.color_combo.setCurrentIndex(1)  # Back to Gray
            self.color_combo.blockSignals(False)
        else:
            # Predefined color selected
            self.current_line_color = color_data
            
            selected_items = self.scene.selectedItems()
            for item in selected_items:
                if isinstance(item, Connection):
                    item.set_line_color(color_data)
                    self.parent_window.statusBar().showMessage(f'Color: {self.color_combo.currentText()}')
                elif isinstance(item, CodeBlock):
                    old_style = {
                        'color': QColor(item.style['color']),
                        'border': QColor(item.style['border']),
                        'alpha': item.style['alpha'],
                        'dashed': item.style['dashed']
                    }
                    new_style = {**old_style, 'color': QColor(color_data)}
                    cmd = ChangeBlockStyleCommand(item, old_style, new_style, "Change Block Color")
                    self.parent_window.undo_stack.push(cmd)
                    self.parent_window.statusBar().showMessage(f'Color: {self.color_combo.currentText()}')

    
    def draw_directory_boundary(self):
        """Draw the directory block"""
        dir_rect = QGraphicsRectItem(0, 0, 3000, 3000)
        dir_rect.setBrush(QBrush(QColor(74, 144, 226, 30)))
        dir_rect.setPen(QPen(QColor(74, 144, 226, 100), 3, Qt.DashLine))
        dir_rect.setZValue(-1)
        self.scene.addItem(dir_rect)
        
        dir_label = QGraphicsTextItem(f"📁 {self.directory_path}")
        dir_label.setDefaultTextColor(QColor(74, 144, 226))
        font = QFont("Arial", 14, QFont.Bold)
        dir_label.setFont(font)
        dir_label.setPos(20, 20)
        dir_label.setZValue(10)
        self.scene.addItem(dir_label)
    
    def on_connection_point_clicked(self, connection_point):
        """Handle click on a connection point - now uses undo command"""
        if self.active_connection_point is None:
            self.active_connection_point = connection_point
            connection_point.set_active(True)
            self.parent_window.statusBar().showMessage('Connection started')
        
        elif self.active_connection_point == connection_point:
            self.active_connection_point.set_active(False)
            self.active_connection_point = None
            self.parent_window.statusBar().showMessage('Connection cancelled')
        
        else:
            from_point = self.active_connection_point
            to_point = connection_point
            
            if from_point.parent_block == to_point.parent_block and from_point.side == to_point.side:
                self.parent_window.statusBar().showMessage('Cannot connect point to itself')
                return
            
            # Use undo command instead of directly creating connection
            command = AddConnectionCommand(
                self,
                from_point.parent_block,
                to_point.parent_block,
                from_point.side,
                to_point.side,
                self.current_flow_type,
                self.current_line_style,
                QColor(self.current_line_color),  # Make a copy of the color
                "Add Connection"
            )
            
            self.parent_window.undo_stack.push(command)
            
            from_point.set_active(False)
            self.active_connection_point = None
            
            self.parent_window.statusBar().showMessage('Connection created!')
    
    def add_block(self, block_data):
        """Add a block to this directory"""
        block = CodeBlock(
            block_data['id'],
            block_data['type'],
            block_data['name'],
            block_data['x'],
            block_data['y'],
            block_data['width'],
            block_data['height'],
            block_data['style'],
            block_data.get('metadata', {}),
            scene_manager=self,
            exists=block_data.get('exists', True)  # Load exists state
        )
        self.scene.addItem(block)
        self.blocks.append(block)
        return block
    
    def add_connection(self, from_block, to_block, from_side='right', to_side='left', 
                      flow_type='one_way', line_style='solid', line_color=None):
        """Add a connection between blocks"""
        if line_color is None:
            line_color = QColor(100, 100, 100)  # Default gray
        conn = Connection(from_block, to_block, from_side, to_side, flow_type, line_style, line_color)
        self.scene.addItem(conn)
        self.connections.append(conn)
        return conn
    
    def get_data(self):
        """Get all blocks and connections as data"""
        return {
            'blocks': [block.to_dict() for block in self.blocks],
            'connections': [
                {
                    'from': conn.from_block.block_id,
                    'to': conn.to_block.block_id,
                    'from_side': conn.from_side,
                    'to_side': conn.to_side,
                    'flow_type': conn.flow_type,
                    'line_style': conn.line_style,
                    'line_color': {
                        'r': conn.line_color.red(),
                        'g': conn.line_color.green(),
                        'b': conn.line_color.blue()
                    }
                }
                for conn in self.connections
            ]
        }
    
    def on_add_function_clicked(self):
        """Handle Add Function/Method button click"""
        # Add function
        self.parent_window.add_function_block()

    def toggle_connection_points(self):
        """Toggle visibility of all connection points"""
        self.show_connections = not self.show_connections
        
        if self.show_connections:
            self.toggle_connections_btn.setText("Hide Connections")
            # Show all connection points on all blocks
            for block in self.blocks:
                for point in block.connection_points.values():
                    point.setVisible(True)
        else:
            self.toggle_connections_btn.setText("Show Connections")
            # Hide all connection points on all blocks
            for block in self.blocks:
                for point in block.connection_points.values():
                    # Hide unless it's red/waiting or parent block is selected
                    if not block.isSelected():
                        point.setVisible(False)
        
        self.parent_window.statusBar().showMessage(
            f"Connection points {'visible' if self.show_connections else 'hidden'}"
        )
