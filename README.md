## SparkChat CLI

针对讯飞的[星火认知大模型](https://xinghuo.xfyun.cn/)创建的api调用demo

---

### Package

```shell
pyinstaller -F main.py
```

---

### Todo

* [x] 完成星火大模型 WebSocket API 封装
* [x] 使用 [PyInquirer](https://github.com/CITGuru/PyInquirer) 封装交互操作
* [x] 使用 [pyinstaller](https://pyinstaller.org/en/stable/) 打包
* [ ] 支持历史对话保存和加载
* [ ] 使用 [Textual](https://github.com/Textualize/textual) 封装为 TUI 应用