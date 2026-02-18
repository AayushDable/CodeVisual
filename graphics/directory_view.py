from PyQt5.QtWidgets import QGraphicsView
from PyQt5.QtCore import Qt
from PyQt5.QtGui import QBrush, QColor, QPainter

from graphics.code_block import CodeBlock
from graphics.connection import Connection

class DirectoryGraphView(QGraphicsView):
    """Graphics view for directory graph with middle-click panning"""
    
    def __init__(self, scene, parent_window):
        super().__init__(scene)
        
        self.parent_window = parent_window
        
        self.setRenderHint(QPainter.Antialiasing)
        self.setRenderHint(QPainter.TextAntialiasing)
        
        self.setDragMode(QGraphicsView.RubberBandDrag)
        
        self.update_theme()
        
        self.setContextMenuPolicy(Qt.CustomContextMenu)
        self.customContextMenuRequested.connect(self.show_context_menu)
        
        self.last_context_pos = None
        
        self.is_panning = False
        self.pan_start_pos = None
        
        # Group selection tracking
        self.is_group_selecting = False
        self.group_start_pos = None
        self.group_end_pos = None

        
    def update_theme(self):
        """Update view theme based on application theme"""
        if hasattr(self.parent_window, 'current_theme'):
            if self.parent_window.current_theme == 'dark':
                self.setBackgroundBrush(QBrush(QColor(45, 45, 45)))
            else:
                self.setBackgroundBrush(QBrush(QColor(245, 245, 245)))
    
    def mousePressEvent(self, event):
        """Handle mouse press for middle-click panning and right-click grouping"""
        if event.button() == Qt.MiddleButton:
            self.is_panning = True
            self.pan_start_pos = event.pos()
            self.setCursor(Qt.ClosedHandCursor)
            event.accept()
        elif event.button() == Qt.RightButton:
            # Start group selection
            self.is_group_selecting = True
            self.group_start_pos = self.mapToScene(event.pos())
            self.group_end_pos = self.group_start_pos
            super().mousePressEvent(event)
        else:
            super().mousePressEvent(event)

    def mouseMoveEvent(self, event):
        """Handle mouse move for panning and group selection"""
        if self.is_panning and self.pan_start_pos:
            delta = event.pos() - self.pan_start_pos
            self.pan_start_pos = event.pos()
            
            self.horizontalScrollBar().setValue(self.horizontalScrollBar().value() - delta.x())
            self.verticalScrollBar().setValue(self.verticalScrollBar().value() - delta.y())
            
            event.accept()
        elif self.is_group_selecting:
            # Update group selection end position
            self.group_end_pos = self.mapToScene(event.pos())
            super().mouseMoveEvent(event)
        else:
            super().mouseMoveEvent(event)

    def mouseReleaseEvent(self, event):
        """Handle mouse release for panning and group selection"""
        if event.button() == Qt.MiddleButton:
            self.is_panning = False
            self.pan_start_pos = None
            self.setCursor(Qt.ArrowCursor)
            event.accept()
        elif event.button() == Qt.RightButton and self.is_group_selecting:
            # End group selection - keep the rectangle info for context menu
            self.is_group_selecting = False
            super().mouseReleaseEvent(event)
        else:
            super().mouseReleaseEvent(event)

    
    def show_context_menu(self, pos):
        """Show context menu on right-click"""
        self.last_context_pos = self.mapToScene(pos)
        
        from PyQt5.QtWidgets import QMenu
        menu = QMenu(self)
        
        item = self.itemAt(pos)
        if isinstance(item, CodeBlock) or (hasattr(item, 'parentItem') and isinstance(item.parentItem(), CodeBlock)):
            block = item if isinstance(item, CodeBlock) else item.parentItem()
            
            rename_action = menu.addAction("✏️ Rename (F2)")
            rename_action.triggered.connect(lambda: block.prompt_rename())

            info_action = menu.addAction("ℹ️ Show Info (Ctrl+I)")
            info_action.triggered.connect(lambda: self.parent_window.show_block_info(block))

            menu.addSeparator()
        
        if isinstance(item, Connection):
            delete_conn_action = menu.addAction("❌ Delete Connection")
            delete_conn_action.triggered.connect(lambda: self.delete_connection(item))
            
            menu.addSeparator()
        
        # Check if we have a valid group selection rectangle
        if self.group_start_pos and self.group_end_pos:
            # Calculate rectangle dimensions
            x1, y1 = self.group_start_pos.x(), self.group_start_pos.y()
            x2, y2 = self.group_end_pos.x(), self.group_end_pos.y()
            
            # Only show if dragged more than 20 pixels (avoid accidental tiny groups)
            if abs(x2 - x1) > 20 and abs(y2 - y1) > 20:
                group_action = menu.addAction("📦 Group")
                group_action.triggered.connect(self.create_group_container)
                menu.addSeparator()
        
        add_function_action = menu.addAction("➕ Add Function Block")
        add_function_action.triggered.connect(self.parent_window.add_function_from_context)
        
        add_method_action = menu.addAction("➕ Add Method Block")
        add_method_action.triggered.connect(self.parent_window.add_method_from_context)

        add_subdir_action = menu.addAction("📁 Add Subdirectory Block")
        add_subdir_action.triggered.connect(self.parent_window.add_subdirectory_from_context)

        add_class_action = menu.addAction("🟡 Add Class Block")
        add_class_action.triggered.connect(self.parent_window.add_class_from_context)

        add_other_action = menu.addAction("📦 Add Other Block")
        add_other_action.triggered.connect(self.parent_window.add_other_from_context) 

        add_image_action = menu.addAction("🖼️ Add Image Block")
        add_image_action.triggered.connect(self.parent_window.add_image_from_context) 

        menu.exec_(self.mapToGlobal(pos))
        
        # Clear group selection after menu closes
        self.group_start_pos = None
        self.group_end_pos = None


    def create_group_container(self):
        """Create a group container from the selection rectangle"""
        if not self.group_start_pos or not self.group_end_pos:
            return
        
        from PyQt5.QtWidgets import QInputDialog
        
        # Ask for group name
        name, ok = QInputDialog.getText(self, 'Group Name', 'Enter group name:')
        
        if not ok or not name:
            return
        
        # Calculate rectangle
        x1, y1 = self.group_start_pos.x(), self.group_start_pos.y()
        x2, y2 = self.group_end_pos.x(), self.group_end_pos.y()
        
        # Normalize (in case dragged right-to-left or bottom-to-top)
        x = min(x1, x2)
        y = min(y1, y2)
        width = abs(x2 - x1)
        height = abs(y2 - y1)
        
        # Call main window to create the group
        self.parent_window.add_group_container(name, x, y, width, height)

    def delete_connection(self, connection):
        """Delete a connection"""
        current_tab = self.parent_window.directory_tabs.get(self.parent_window.current_directory)
        if current_tab and connection in current_tab.connections:
            current_tab.connections.remove(connection)
            
            if connection.arrow_end and connection.arrow_end.scene():
                self.scene().removeItem(connection.arrow_end)
            if connection.arrow_start and connection.arrow_start.scene():
                self.scene().removeItem(connection.arrow_start)
            
            self.scene().removeItem(connection)
            self.parent_window.statusBar().showMessage('Connection deleted')
    
    def wheelEvent(self, event):
        """Zoom with mouse wheel"""
        zoom_factor = 1.15
        
        if event.angleDelta().y() > 0:
            self.scale(zoom_factor, zoom_factor)
        else:
            self.scale(1/zoom_factor, 1/zoom_factor)

