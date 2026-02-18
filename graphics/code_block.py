import os
from PyQt5.QtWidgets import (QGraphicsItem, QGraphicsRectItem,
                             QGraphicsTextItem, QInputDialog, QLineEdit,
                             QGraphicsEllipseItem)
from PyQt5.QtCore import Qt, QRectF, QPointF
from PyQt5.QtGui import QPen, QBrush, QColor, QFont
from PyQt5.QtGui import QPixmap



from graphics.connection import Connection
from graphics.connection_point import ConnectionPoint

from PyQt5.QtSvg import QSvgRenderer
from PyQt5.QtGui import QPainter


class ResizeHandle(QGraphicsEllipseItem):
    """Handle for resizing blocks"""
    
    def __init__(self, parent_block, position):
        super().__init__(-4, -4, 8, 8)  # 8x8 handle
        
        self.parent_block = parent_block
        self.position = position  # 'top-left', 'top-right', 'bottom-left', 'bottom-right'
        
        self.setBrush(QBrush(QColor(33, 150, 243, 180)))
        self.setPen(QPen(QColor(25, 118, 210), 1))
        self.setZValue(100)
        
        self.setParentItem(parent_block)
        self.setFlag(QGraphicsItem.ItemIsSelectable, False)
        self.setAcceptedMouseButtons(Qt.LeftButton)

        # Set cursor based on position
        if position in ['top-left', 'bottom-right']:
            self.setCursor(Qt.SizeFDiagCursor)
        else:
            self.setCursor(Qt.SizeBDiagCursor)
        
        self.is_resizing = False
        self.resize_start_pos = None
        self.original_rect = None
        
        self.update_position()
    
    def update_position(self):
        """Update handle position based on parent block size"""
        rect = self.parent_block.rect()
        
        if self.position == 'top-left':
            self.setPos(0, 0)
        elif self.position == 'top-right':
            self.setPos(rect.width(), 0)
        elif self.position == 'bottom-left':
            self.setPos(0, rect.height())
        elif self.position == 'bottom-right':
            self.setPos(rect.width(), rect.height())
    
    def mousePressEvent(self, event):
        """Start resizing"""
        if event.button() == Qt.LeftButton:
            self.is_resizing = True
            self.resize_start_pos = event.scenePos()
            self.original_rect = self.parent_block.rect()
            event.accept()
        else:
            super().mousePressEvent(event)
    
    def mouseMoveEvent(self, event):
        """Handle resizing"""
        if self.is_resizing and self.resize_start_pos:
            delta = event.scenePos() - self.resize_start_pos
            
            new_rect = QRectF(self.original_rect)
            
            # Minimum size
            min_width = 100
            min_height = 50
            
            if self.position == 'bottom-right':
                new_rect.setWidth(max(self.original_rect.width() + delta.x(), min_width))
                new_rect.setHeight(max(self.original_rect.height() + delta.y(), min_height))
            
            elif self.position == 'top-right':
                new_rect.setWidth(max(self.original_rect.width() + delta.x(), min_width))
                new_height = max(self.original_rect.height() - delta.y(), min_height)
                if new_height >= min_height:
                    new_rect.setTop(self.original_rect.top() + delta.y())
                    new_rect.setHeight(new_height)
            
            elif self.position == 'bottom-left':
                new_width = max(self.original_rect.width() - delta.x(), min_width)
                if new_width >= min_width:
                    new_rect.setLeft(self.original_rect.left() + delta.x())
                    new_rect.setWidth(new_width)
                new_rect.setHeight(max(self.original_rect.height() + delta.y(), min_height))
            
            elif self.position == 'top-left':
                new_width = max(self.original_rect.width() - delta.x(), min_width)
                new_height = max(self.original_rect.height() - delta.y(), min_height)
                if new_width >= min_width:
                    new_rect.setLeft(self.original_rect.left() + delta.x())
                    new_rect.setWidth(new_width)
                if new_height >= min_height:
                    new_rect.setTop(self.original_rect.top() + delta.y())
                    new_rect.setHeight(new_height)
            
            self.parent_block.setRect(new_rect)
            self.parent_block.on_resize()
            
            event.accept()
        else:
            super().mouseMoveEvent(event)
    
    def mouseReleaseEvent(self, event):
        """Stop resizing"""
        if event.button() == Qt.LeftButton:
            self.is_resizing = False
            self.resize_start_pos = None
            self.original_rect = None
            event.accept()
        else:
            super().mouseReleaseEvent(event)



class CodeBlock(QGraphicsRectItem):
    """Represents a function, subdirectory, or class block"""
    
    BLOCK_TYPES = {
        'FUNCTION': {'color': QColor(255, 255, 255), 'border': QColor(0, 0, 0, 100), 
                    'alpha': 255, 'dashed': False},
        'SUBDIRECTORY': {'color': QColor(30, 58, 95), 'border': QColor(13, 31, 60, 100), 
                        'alpha': 180, 'dashed': True},
        'CLASS': {'color': QColor(255, 250, 205), 'border': QColor(218, 165, 32, 100), 
                'alpha': 200, 'dashed': True},
        'METHOD': {'color': QColor(230, 200, 255), 'border': QColor(138, 43, 226, 100), 
                'alpha': 255, 'dashed': False},
        'OTHER': {'color': QColor(200, 200, 200), 'border': QColor(128, 128, 128, 100), 
                'alpha': 200, 'dashed': False},
        'GROUP': {'color': QColor(220, 240, 255), 'border': QColor(100, 150, 200, 100), 
                'alpha': 100, 'dashed': True},  # Light blue, semi-transparent
        'IMAGE': {'color': QColor(255, 255, 255), 'border': QColor(100, 100, 100, 0), 
                'alpha': 0, 'dashed': False},  # No background for images
    }


    def __init__(self, block_id, block_type, name, x, y, width, height, style, metadata=None, scene_manager=None, exists=True):
        super().__init__(0, 0, width, height)
        
        self.block_id = block_id
        self.block_type = block_type
        self.name = name
        self.display_name = name
        self.metadata = metadata or {}
        self.scene_manager = scene_manager
        self.exists = exists  # Track if function/directory/class exists

        # Image-specific attributes
        self.image_item = None
        self.image_path = metadata.get('image_path', '') if metadata else ''

        self.block_color = None
        self.block_border_color = None
        
        self.style = {}
        
        if block_type == 'GROUP':
            self.setZValue(-2)  # Behind directory boundary (-1)

        if 'alias' in self.metadata:
            self.display_name = self.metadata['alias']
        
        self.setPos(x, y)
        
        self.setFlags(QGraphicsItem.ItemIsMovable | 
                     QGraphicsItem.ItemIsSelectable |
                     QGraphicsItem.ItemSendsGeometryChanges |
                     QGraphicsItem.ItemIsFocusable)
        
        self.setAcceptedMouseButtons(Qt.LeftButton | Qt.RightButton)
        
        self.load_style_settings(style)
        self.update_style()

        if block_type == 'IMAGE':
            self.create_image_display()
        else:
            self.text_item = QGraphicsTextItem(self.display_name, self)
            self.text_item.setDefaultTextColor(Qt.black)
            
            # Bold for subdirectories and classes
            is_bold = block_type in ['SUBDIRECTORY', 'CLASS', 'GROUP']
            font = QFont("Arial", 10, QFont.Bold if is_bold else QFont.Normal)
            self.text_item.setFont(font)
            
            self.center_text()
        
        self.connection_points = {}
        if scene_manager:
            self.create_connection_points()
        
        # Create resize handles
        self.resize_handles = {}
        self.create_resize_handles()
    
    def set_exists(self, exists):
        """Set whether this block exists in filesystem and update style"""
        self.exists = exists
        self.update_style()

    def load_style_settings(self,style):
        if style['color'] == (None,None,None):
            self.style['color'] = self.BLOCK_TYPES[self.block_type]['color']
        else:
            self.style['color'] = QColor(style['color'][0],style['color'][1],style['color'][2])
        if style['border'] == (None,None,None,None):
            self.style['border'] = self.BLOCK_TYPES[self.block_type]['border']
        else:
            self.style['border'] = QColor(style['border'][0],style['border'][1],style['border'][2],style['border'][3])
        if style['alpha'] == None:
            self.style['alpha'] = self.BLOCK_TYPES[self.block_type]['alpha']
        else:
            self.style['alpha'] = style['alpha']
        if style['dashed'] == None:
            self.style['dashed'] = self.BLOCK_TYPES[self.block_type]['dashed']
        else:
            self.style['dashed'] = style['dashed']

    def create_resize_handles(self):
        """Create resize handles at corners"""
        positions = ['top-left', 'top-right', 'bottom-left', 'bottom-right']
        for pos in positions:
            handle = ResizeHandle(self, pos)
            self.resize_handles[pos] = handle
            handle.setVisible(False)  # Hidden by default
    
    def update_resize_handles(self):
        """Update resize handle positions"""
        for handle in self.resize_handles.values():
            handle.update_position()
    
    def paint(self, painter, option, widget=None):
        """Custom paint to show/hide resize handles and connection points based on selection"""
        super().paint(painter, option, widget)
        
        is_selected = self.isSelected()
        
        # Show/hide resize handles
        for handle in self.resize_handles.values():
            handle.setVisible(is_selected)
        
        # Show/hide connection points
        if self.scene_manager:  # scene_manager is the DirectoryTab
            show_all = getattr(self.scene_manager, 'show_connections', False)
            
            for point in self.connection_points.values():
                # Always show red/waiting points
                if show_all:
                    point.setVisible(True)  # Show all when toggle is on
                else:
                    point.setVisible(is_selected)  # Show only when selected
        else:
            # Fallback if no scene_manager
            for point in self.connection_points.values():
                point.setVisible(is_selected)

        
    def on_resize(self):
        """Called when block is resized"""
        self.center_text()
        self.update_connection_points()
        self.update_resize_handles()
        if self.block_type == 'IMAGE':
            self.load_and_scale_image()
        # Update connections
        if self.scene():
            for item in self.scene().items():
                if isinstance(item, Connection):
                    if item.from_block == self or item.to_block == self:
                        item.update_path()
    
    def create_connection_points(self):
        """Create connection points on all four sides"""
        for side in ['top', 'bottom', 'left', 'right']:
            point = ConnectionPoint(self, side, self.scene_manager)
            self.connection_points[side] = point
            point.setVisible(False)  # Hide by default

    def update_connection_points(self):
        """Update connection point positions after resize"""
        for point in self.connection_points.values():
            point.update_position()
    
    def center_text(self):
        """Center text in the block"""
        from PyQt5.QtGui import QTextOption

        # Skip text centering for IMAGE blocks
        if self.block_type == 'IMAGE':
            return
        
        # Enable text wrapping based on block width
        available_width = self.rect().width() - 20  # 10px padding on each side
        self.text_item.setTextWidth(available_width)
        
        if self.block_type == 'GROUP':
            # For GROUP, align text to top-left with wrapping
            text_option = QTextOption(Qt.AlignLeft | Qt.AlignTop)
            self.text_item.document().setDefaultTextOption(text_option)
            self.text_item.setPos(10, 5)
        else:
            # For other blocks, center-align the text
            text_option = QTextOption(Qt.AlignHCenter)
            self.text_item.document().setDefaultTextOption(text_option)
            
            # Position the text item container
            text_rect = self.text_item.boundingRect()
            text_x = 10  # Left padding (text is centered within the width)
            text_y = (self.rect().height() - text_rect.height()) / 2
            self.text_item.setPos(text_x, text_y)


    
    def set_alias(self, alias):
        """Set an alias for display name"""
        if alias and alias.strip():
            self.display_name = alias.strip()
            self.metadata['alias'] = self.display_name
        else:
            self.display_name = self.name
            if 'alias' in self.metadata:
                del self.metadata['alias']
        
        self.text_item.setPlainText(self.display_name)
        self.auto_resize_to_text()
    
    def auto_resize_to_text(self):
        """Automatically resize block to fit text with padding"""
        text_rect = self.text_item.boundingRect()
        
        padding_x = 40
        padding_y = 30
        
        new_width = max(text_rect.width() + padding_x, 150)
        new_height = max(text_rect.height() + padding_y, 60)
        
        self.setRect(0, 0, new_width, new_height)
        
        self.center_text()
        self.update_connection_points()
        self.update_resize_handles()
        
        if self.scene():
            self.scene().update()
    

    def select_contained_items(self):
        """Select all items fully contained within this GROUP block"""
        if self.block_type != 'GROUP' or not self.scene():
            return
        
        group_rect = self.sceneBoundingRect()
        
        for item in self.scene().items():
            if isinstance(item, CodeBlock) and item != self:
                item_rect = item.sceneBoundingRect()
                # Check if item is fully contained
                if group_rect.contains(item_rect):
                    item.setSelected(True)


    def itemChange(self, change, value):
        """Handle item changes"""
        if change == QGraphicsItem.ItemSelectedHasChanged:
            if value and self.block_type == 'GROUP':  # GROUP was selected
                self.select_contained_items()
        
        if change == QGraphicsItem.ItemPositionChange and self.block_type == 'GROUP':
            # GROUP is being moved, move contained items too
            if self.scene():
                new_pos = value  # New position of the GROUP
                old_pos = self.pos()  # Current position
                delta = new_pos - old_pos  # Calculate the movement delta
                
                # Move all contained items by the same delta
                self.move_contained_items(delta)
        
        if change == QGraphicsItem.ItemPositionHasChanged:
            if self.scene():
                for item in self.scene().items():
                    if isinstance(item, Connection):
                        if item.from_block == self or item.to_block == self:
                            item.update_path()
        
        return super().itemChange(change, value)

    def move_contained_items(self, delta):
        """Move all contained items by the given delta"""
        if not self.scene():
            return
        
        group_rect = self.sceneBoundingRect()
        
        for item in self.scene().items():
            if isinstance(item, CodeBlock) and item != self and item.isSelected():
                # Check if item is contained
                item_center = item.sceneBoundingRect().center()
                if group_rect.contains(item_center):
                    item.moveBy(delta.x(), delta.y())

    
    def keyPressEvent(self, event):
        """Handle key press events"""
        if event.key() == Qt.Key_F2:
            self.prompt_rename()
        else:
            super().keyPressEvent(event)
    
    def prompt_rename(self):
        """Prompt user to rename the block"""
        current_name = self.display_name
        
        alias, ok = QInputDialog.getText(
            None, 
            'Rename Block (Alias)', 
            f'Original: {self.name}\n\nEnter display name:',
            QLineEdit.Normal,
            current_name
        )
        
        if ok:
            self.set_alias(alias)
    
    def update_style(self):
        """Update block visual style"""
        
        color = QColor(self.style['color'])
        color.setAlpha(self.style['alpha'])
        self.setBrush(QBrush(color))
        
        # Use red border if doesn't exist, otherwise normal border
        if not self.exists:
            border_color = QColor(220, 53, 69)  # Red
            pen = QPen(border_color)
            pen.setWidth(3)  # Thicker for visibility
        else:
            border_color = self.style['border']
            pen = QPen(border_color)
            pen.setWidth(2)
        
        if self.style['dashed']:
            pen.setStyle(Qt.DashLine)
        
        self.setPen(pen)
    
    def to_dict(self):
        """Convert block to dictionary"""

        # Fixed — preserves alpha
        style_dict = {
            'color': (self.style['color'].red(), self.style['color'].green(), self.style['color'].blue()),
            'border': (self.style['border'].red(), self.style['border'].green(), self.style['border'].blue(), self.style['border'].alpha()),
            'alpha': self.style['alpha'],
            'dashed': self.style['dashed']
        }


        return {
            'id': self.block_id,
            'type': self.block_type,
            'name': self.name,
            'x': self.pos().x(),
            'y': self.pos().y(),
            'width': self.rect().width(),
            'height': self.rect().height(),
            'style': style_dict,
            'metadata': self.metadata,
            'exists': self.exists  # Save existence state
        }

    def create_image_display(self):
        """Create and display image for IMAGE block type"""
        from PyQt5.QtWidgets import QGraphicsPixmapItem

        # Create pixmap item for the image
        if self.image_path and os.path.exists(self.image_path):
            self.image_item = QGraphicsPixmapItem(self)
            self.load_and_scale_image()
        else:
            # Show placeholder if no image
            self.image_item = None
    
    def load_and_scale_image(self):
        """Load and scale image to fit within the block"""
        if not self.image_path or not os.path.exists(self.image_path):
            return
        
        # Calculate scaling to fit within block with padding
        available_width = self.rect().width() - 5
        available_height = self.rect().height() - 5
        
        # Get device pixel ratio for sharp rendering
        if self.scene() and self.scene().views():
            dpr = self.scene().views()[0].devicePixelRatioF()
        else:
            dpr = 1.0
        
        if self.image_path.lower().endswith('.svg'):
            # SVG: Render at physical pixel size for sharpness
            renderer = QSvgRenderer(self.image_path)
            
            # Get SVG aspect ratio
            svg_size = renderer.defaultSize()
            aspect_ratio = svg_size.width() / svg_size.height() if svg_size.height() > 0 else 1.0
            
            # Calculate display size maintaining aspect ratio
            if available_width / available_height > aspect_ratio:
                display_height = available_height
                display_width = available_height * aspect_ratio
            else:
                display_width = available_width
                display_height = available_width / aspect_ratio
            
            # Create pixmap at physical pixel dimensions
            pixmap = QPixmap(int(display_width * dpr), int(display_height * dpr))
            pixmap.fill(Qt.transparent)
            pixmap.setDevicePixelRatio(dpr)
            
            # Render SVG to pixmap with antialiasing
            painter = QPainter(pixmap)
            painter.setRenderHints(QPainter.Antialiasing | QPainter.SmoothPixmapTransform)
            renderer.render(painter)
            painter.end()
        else:
            # Raster image: Load and scale with DPR
            pixmap = QPixmap(self.image_path)
            
            if pixmap.isNull():
                print(f"Failed to load image: {self.image_path}")
                return
            
            # Scale to physical pixels
            scaled_pixmap = pixmap.scaled(
                int(available_width * dpr),
                int(available_height * dpr),
                Qt.KeepAspectRatio,
                Qt.SmoothTransformation
            )
            scaled_pixmap.setDevicePixelRatio(dpr)
            pixmap = scaled_pixmap
        
        if self.image_item:
            self.image_item.setPixmap(pixmap)
            
            # Center the image in the block (use logical size for positioning)
            image_rect = self.image_item.boundingRect()
            x = (self.rect().width() - image_rect.width()) / 2
            y = (self.rect().height() - image_rect.height()) / 2
            self.image_item.setPos(x, y)


    def set_image_path(self, path):
        """Set or update the image path for IMAGE blocks"""
        if self.block_type != 'IMAGE':
            return
        
        self.image_path = path
        self.metadata['image_path'] = path
        
        if not self.image_item:
            from PyQt5.QtWidgets import QGraphicsPixmapItem
            self.image_item = QGraphicsPixmapItem(self)
        
        self.load_and_scale_image()