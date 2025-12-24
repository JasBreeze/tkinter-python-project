import tkinter as tk
import sys
import traceback

# 添加调试信息
try:
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
except Exception as e:
    print(f"发生错误: {e}", file=sys.stderr)
    traceback.print_exc(file=sys.stderr)
    # 等待用户输入，以便查看错误信息
    input("按回车键退出...")


