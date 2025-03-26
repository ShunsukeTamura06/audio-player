# WAVファイル連続再生オーディオプレーヤー

Jupyter Notebook上で動作するWAVファイル連続再生用のオーディオプレーヤーです。

## 特徴

- 複数のWAVファイルを連続再生（指定した間隔で自動結合）
- 再生中のファイル名表示
- 再生/一時停止/停止ボタン
- スライダーによる再生位置の制御
- Jupyterウィジェットを使用したインタラクティブなインターフェース

## 必要条件

- Python 3.6以上
- Jupyter Notebook または JupyterLab
- 以下のPythonライブラリ：
  - numpy
  - ipywidgets
  - pydub
  - simpleaudio（オプション、再生位置の詳細な制御に使用）

## インストール

```bash
pip install numpy ipywidgets pydub simpleaudio
```

## 使用方法

1. `outputs`フォルダ（またはカスタム指定したフォルダ）に再生したいWAVファイルを配置
2. Jupyter Notebookで`example_usage.ipynb`を開く
3. ノートブックのセルを実行

```python
from audio_player import create_audio_player

# デフォルト設定でプレーヤーを作成
player = create_audio_player()

# または、カスタム設定でプレーヤーを作成
# player = create_audio_player(folder='カスタムフォルダ', gap_seconds=5)
```

## ライセンス

MIT

## 作者

ShunsukeTamura06