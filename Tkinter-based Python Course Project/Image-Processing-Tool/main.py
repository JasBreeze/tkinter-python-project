from controllers import EditorController
from views import ModernEditorView

if __name__ == "__main__":
    # 创建控制器
    controller = EditorController(None)
    # 创建视图，并将控制器传递给视图
    view = ModernEditorView(controller)
    # 将视图传递给控制器
    controller.view = view
    # 运行应用
    view.mainloop()