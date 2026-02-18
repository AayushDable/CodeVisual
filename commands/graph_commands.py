from PyQt5.QtWidgets import QUndoCommand
from PyQt5.QtGui import QColor
from graphics.code_block import CodeBlock
from graphics.connection import Connection


class AddBlockCommand(QUndoCommand):
    """Command to add a block"""
    
    def __init__(self, tab, block_data, main_window, description="Add Block"):
        super().__init__(description)
        self.tab = tab
        self.block_data = block_data
        self.main_window = main_window
        self.block = None
    
    def redo(self):
        """Add the block"""
        self.block = self.tab.add_block(self.block_data)
        
        # Set up double-click handler
        if self.block.block_type == 'SUBDIRECTORY':
            self.block.mouseDoubleClickEvent = lambda event, b=self.block: self.main_window.open_subdirectory(b)
        elif self.block.block_type == 'FUNCTION':
            self.block.mouseDoubleClickEvent = lambda event, b=self.block: self.main_window.open_function(b)
        elif self.block.block_type == 'METHOD':
            self.block.mouseDoubleClickEvent = lambda event, b=self.block: self.main_window.open_function(b)
        elif self.block.block_type == 'CLASS':
            self.block.mouseDoubleClickEvent = lambda event, b=self.block: self.main_window.open_class(b)

        # Update subdirectory list if it's a subdirectory
        if self.block.block_type in ['SUBDIRECTORY', 'CLASS']:
            subdir_path = f"{self.main_window.current_directory}/{self.block.name}"
            if subdir_path not in self.main_window.directory_data:
                self.main_window.directory_data[subdir_path] = {'blocks': [], 'connections': []}
            self.main_window.refresh_subdirectories()
    
    def undo(self):
        """Remove the block"""
        if self.block:
            # Remove from blocks list
            if self.block in self.tab.blocks:
                self.tab.blocks.remove(self.block)
            
            # Remove all connected connections
            connections_to_remove = [
                conn for conn in self.tab.connections 
                if conn.from_block == self.block or conn.to_block == self.block
            ]
            
            for conn in connections_to_remove:
                if conn.arrow_end and conn.arrow_end.scene():
                    self.tab.scene.removeItem(conn.arrow_end)
                if conn.arrow_start and conn.arrow_start.scene():
                    self.tab.scene.removeItem(conn.arrow_start)
                if conn.scene():
                    self.tab.scene.removeItem(conn)
                if conn in self.tab.connections:
                    self.tab.connections.remove(conn)
            
            # Remove from scene
            if self.block.scene():
                self.tab.scene.removeItem(self.block)
            
            # Remove directory data for SUBDIRECTORY or CLASS blocks
            if self.block.block_type in ['SUBDIRECTORY', 'CLASS']:
                dir_path = f"{self.main_window.current_directory}/{self.block.name}"
                if dir_path in self.main_window.directory_data:
                    del self.main_window.directory_data[dir_path]
                self.main_window.refresh_subdirectories()



class DeleteBlockCommand(QUndoCommand):
    """Command to delete a block"""
    
    def __init__(self, tab, block, main_window, description="Delete Block"):
        super().__init__(description)
        self.tab = tab
        self.block = block
        self.main_window = main_window
        self.block_data = block.to_dict()
        
        # Store connections that will be deleted
        self.deleted_connections = []
        for conn in tab.connections:
            if conn.from_block == block or conn.to_block == block:
                self.deleted_connections.append({
                    'connection': conn,
                    'from_block': conn.from_block,
                    'to_block': conn.to_block,
                    'from_side': conn.from_side,
                    'to_side': conn.to_side,
                    'flow_type': conn.flow_type,
                    'line_style': conn.line_style,
                    'line_color': QColor(conn.line_color)
                })
    
    def redo(self):
        """Delete the block"""
        # Remove from blocks list
        if self.block in self.tab.blocks:
            self.tab.blocks.remove(self.block)
        
        # Remove all connected connections
        for conn_data in self.deleted_connections:
            conn = conn_data['connection']
            if conn.arrow_end and conn.arrow_end.scene():
                self.tab.scene.removeItem(conn.arrow_end)
            if conn.arrow_start and conn.arrow_start.scene():
                self.tab.scene.removeItem(conn.arrow_start)
            if conn.scene():
                self.tab.scene.removeItem(conn)
            if conn in self.tab.connections:
                self.tab.connections.remove(conn)
        
        # Remove from scene
        if self.block.scene():
            self.tab.scene.removeItem(self.block)
        
        # Remove directory data for SUBDIRECTORY or CLASS blocks
        if self.block.block_type in ['SUBDIRECTORY', 'CLASS']:
            dir_path = f"{self.main_window.current_directory}/{self.block.name}"
            if dir_path in self.main_window.directory_data:
                del self.main_window.directory_data[dir_path]
            self.main_window.refresh_subdirectories()


    
    def undo(self):
        """Restore the block"""
        # Re-add block
        self.block = self.tab.add_block(self.block_data)
        
        # Set up double-click handler
        if self.block.block_type == 'SUBDIRECTORY':
            self.block.mouseDoubleClickEvent = lambda event, b=self.block: self.main_window.open_subdirectory(b)
        elif self.block.block_type == 'FUNCTION':
            self.block.mouseDoubleClickEvent = lambda event, b=self.block: self.main_window.open_function(b)
        elif self.block.block_type == 'METHOD':
            self.block.mouseDoubleClickEvent = lambda event, b=self.block: self.main_window.open_function(b)
        elif self.block.block_type == 'CLASS':
            self.block.mouseDoubleClickEvent = lambda event, b=self.block: self.main_window.open_class(b)


        # Restore connections
        for conn_data in self.deleted_connections:
            conn = Connection(
                conn_data['from_block'],
                conn_data['to_block'],
                conn_data['from_side'],
                conn_data['to_side'],
                conn_data['flow_type'],
                conn_data['line_style'],
                conn_data['line_color']
            )
            self.tab.scene.addItem(conn)
            conn.update_path()
            self.tab.connections.append(conn)
            conn_data['connection'] = conn
        
        # Update subdirectory and classes list
        if self.block.block_type in ['SUBDIRECTORY', 'CLASS']:
            self.main_window.refresh_subdirectories()

class AddConnectionCommand(QUndoCommand):
    """Command to add a connection"""
    
    def __init__(self, tab, from_block, to_block, from_side, to_side, flow_type, line_style, line_color, description="Add Connection"):
        super().__init__(description)
        self.tab = tab
        self.from_block = from_block
        self.to_block = to_block
        self.from_side = from_side
        self.to_side = to_side
        self.flow_type = flow_type
        self.line_style = line_style
        self.line_color = line_color
        self.connection = None
    
    def redo(self):
        """Add the connection"""
        self.connection = Connection(
            self.from_block,
            self.to_block,
            self.from_side,
            self.to_side,
            self.flow_type,
            self.line_style,
            self.line_color
        )
        self.tab.scene.addItem(self.connection)
        self.connection.update_path()
        self.tab.connections.append(self.connection)
    
    def undo(self):
        """Remove the connection"""
        if self.connection:
            if self.connection.arrow_end and self.connection.arrow_end.scene():
                self.tab.scene.removeItem(self.connection.arrow_end)
            if self.connection.arrow_start and self.connection.arrow_start.scene():
                self.tab.scene.removeItem(self.connection.arrow_start)
            if self.connection in self.tab.connections:
                self.tab.connections.remove(self.connection)
            if self.connection.scene():
                self.tab.scene.removeItem(self.connection)


class DeleteConnectionCommand(QUndoCommand):
    """Command to delete a connection"""
    
    def __init__(self, tab, connection, description="Delete Connection"):
        super().__init__(description)
        self.tab = tab
        self.connection = connection
        self.from_block = connection.from_block
        self.to_block = connection.to_block
        self.from_side = connection.from_side
        self.to_side = connection.to_side
        self.flow_type = connection.flow_type
        self.line_style = connection.line_style
        self.line_color = QColor(connection.line_color)
    
    def redo(self):
        """Delete the connection"""
        if self.connection.arrow_end and self.connection.arrow_end.scene():
            self.tab.scene.removeItem(self.connection.arrow_end)
        if self.connection.arrow_start and self.connection.arrow_start.scene():
            self.tab.scene.removeItem(self.connection.arrow_start)
        if self.connection in self.tab.connections:
            self.tab.connections.remove(self.connection)
        if self.connection.scene():
            self.tab.scene.removeItem(self.connection)
    
    def undo(self):
        """Restore the connection"""
        self.connection = Connection(
            self.from_block,
            self.to_block,
            self.from_side,
            self.to_side,
            self.flow_type,
            self.line_style,
            self.line_color
        )
        self.tab.scene.addItem(self.connection)
        self.connection.update_path()
        self.tab.connections.append(self.connection)


class MoveBlockCommand(QUndoCommand):
    """Command to move a block"""
    
    def __init__(self, block, old_pos, new_pos, description="Move Block"):
        super().__init__(description)
        self.block = block
        self.old_pos = old_pos
        self.new_pos = new_pos
    
    def redo(self):
        """Move to new position"""
        self.block.setPos(self.new_pos)
    
    def undo(self):
        """Move to old position"""
        self.block.setPos(self.old_pos)


class RenameBlockCommand(QUndoCommand):
    """Command to rename a block"""
    
    def __init__(self, block, old_name, new_name, description="Rename Block"):
        super().__init__(description)
        self.block = block
        self.old_name = old_name
        self.new_name = new_name
    
    def redo(self):
        """Apply new name"""
        self.block.set_alias(self.new_name)
    
    def undo(self):
        """Restore old name"""
        self.block.set_alias(self.old_name)

class ChangeBlockStyleCommand(QUndoCommand):
    def __init__(self, block, old_style, new_style, description="Change Block Style"):
        super().__init__(description)
        self.block = block
        self.old_style = {
            'color': QColor(old_style['color']),
            'border': QColor(old_style['border']),
            'alpha': old_style['alpha'],
            'dashed': old_style['dashed']
        }
        self.new_style = {
            'color': QColor(new_style['color']),
            'border': QColor(new_style['border']),
            'alpha': new_style['alpha'],
            'dashed': new_style['dashed']
        }

    def redo(self):
        self._apply_style(self.new_style)

    def undo(self):
        self._apply_style(self.old_style)

    def _apply_style(self, style):
        self.block.style['color'] = QColor(style['color'])
        self.block.style['border'] = QColor(style['border'])
        self.block.style['alpha'] = style['alpha']
        self.block.style['dashed'] = style['dashed']
        self.block.update_style()
