from controllers import EditorController
from views import ModernEditorView

if __name__ == "__main__":
    # 初始化应用
    controller = EditorController(None)
    view = ModernEditorView(controller)
    controller.view = view
    
    # 初始化tkinter变量
    controller._init_tk_variables()
    
    # 启动应用
    view.mainloop()