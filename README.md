# CodeGrapher

A graphical code navigation and documentation tool for Python projects. Create interactive flowcharts and diagrams to map out your codebase structure, functions, classes, and their relationships.

## Features

- **Visual and Interactive Code Mapping**: Represent Python functions, classes, subdirectories, and custom elements as interactive blocks
- **Smart Connections**: Draw typed connections between blocks with different flow types (control flow, data flow, inheritance, etc.)
- **Auto-Validation**: Automatically verify that functions and classes still exist in your codebase with visual indicators
- **Directory Navigation**: Navigate through your project structure with nested subdirectory support
- **Image Support**: Add custom images and icons (SVG, PNG, JPG) to your diagrams with sharp vector rendering
- **Undo/Redo**: Full undo/redo support for all operations
- **Export**: Save your diagrams as JSON for version control and sharing

## Installation

```bash
pip install -r requirements.txt
```

Run the vbscript file to start the application. 
## Usage

1. **Set Root Path**: Point to your Python project directory
2. **Add Blocks**: Create blocks for functions, classes, subdirectories, or custom elements
3. **Connect Blocks**: Draw connections between blocks to show relationships
4. **Validate**: Use the validate feature to check if code elements still exist in your filesystem
5. **Navigate**: Double-click subdirectory or class blocks to navigate into them
6. **Save**: Export your diagram to JSON format

## Block Types

- **FUNCTION**: Python functions (white background)
- **CLASS**: Python classes (light yellow background)
- **METHOD**: Class methods (light purple background)
- **SUBDIRECTORY**: Nested directories (dark blue, dashed border)
- **GROUP**: Visual grouping container (light blue, semi-transparent)
- **IMAGE**: Custom images/icons (transparent background)
- **OTHER**: Custom elements (gray background)

## Keyboard Shortcuts

- **F2**: Rename selected block (add alias)
- **Delete**: Delete selected block or connection
- **Ctrl+Z**: Undo
- **Ctrl+Y**: Redo

## Connection Types

- **Control Flow**: Execution flow between functions
- **Data Flow**: Data passing between components
- **Dependency**: Module/function dependencies
- **Inheritance**: Class inheritance relationships
- **Association**: General associations

## Status Indicators

- **Green/Normal border**: Element exists in filesystem
- **Red thick border**: Element missing or moved (after validation)

## File Structure

- Diagrams are saved as JSON files with `.json` extension
- Each directory level can have its own diagram
- Metadata includes positions, connections, and code references

## Requirements

- Python 3.6+
- PyQt5
- Project works with any Python codebase

## Tips

- Use **GROUP** blocks to organize related components
- Enable "Show Connections" to see all connection points
- Run validation regularly to keep diagrams in sync with code
- Use aliases (F2) to simplify long function/class names in diagrams
- Resize blocks by selecting them and dragging corner handles

Replace your **Credits** section with this (wording is intentionally explicit):

## License

This project is licensed under MIT LICENSE - see the [LICENSE](LICENSE) file for details.

Third-party components are licensed under their respective licenses - see [THIRD-PARTY-LICENSES.txt](THIRD-PARTY-LICENSES.txt) for details.

##
**Note**: This tool creates visual elements separate from your code. It doesn't modify your Python files.
