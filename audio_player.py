import os
import numpy as np
import ipywidgets as widgets
from IPython.display import display, Audio, clear_output
import time
from threading import Thread
import tempfile
from pydub import AudioSegment
import wave

# 高度な再生制御のためにsimpleaudioをインポート試行
try:
    import simpleaudio as sa
    HAVE_SIMPLEAUDIO = True
except ImportError:
    HAVE_SIMPLEAUDIO = False


def get_wav_files(folder="outputs"):
    """指定されたフォルダからすべてのWAVファイルを取得する"""
    wav_files = []
    for file in os.listdir(folder):
        if file.lower().endswith('.wav'):
            wav_files.append(os.path.join(folder, file))
    return sorted(wav_files)  # 一貫した順序を確保するためにソート

def combine_wav_files(wav_files, gap_seconds=3):
    """
    複数のWAVファイルを間隔を空けて結合し、位置を追跡する
    
    Args:
        wav_files: WAVファイルパスのリスト
        gap_seconds: ファイル間の無音の秒数
        
    Returns:
        combined_audio: 結合されたAudioSegment
        file_positions: ファイル名とタイムスタンプ位置を含む辞書のリスト
    """
    if not wav_files:
        raise ValueError("WAVファイルが見つかりません。")
    
    # 新しい結合オーディオを作成
    combined = AudioSegment.empty()
    
    # 各ファイルのタイムスタンプを追跡
    file_positions = []
    current_position = 0
    
    # 各ファイルを間隔を空けて追加
    silence = AudioSegment.silent(duration=gap_seconds * 1000)  # pydubはミリ秒単位を使用
    
    for wav_file in wav_files:
        # このファイルの開始位置を記録
        file_positions.append({
            'file': os.path.basename(wav_file),
            'start': current_position,
            'end': None  # 後で埋める
        })
        
        # オーディオファイルを読み込んで追加
        audio = AudioSegment.from_wav(wav_file)
        combined += audio
        
        # このファイルの終了位置を記録
        file_positions[-1]['end'] = len(combined) / 1000.0  # 秒に変換
        current_position = len(combined) / 1000.0
        
        # 次のファイルの前に無音を追加（最後のファイル以外）
        if wav_file != wav_files[-1]:
            combined += silence
            current_position += gap_seconds
    
    return combined, file_positions

def save_combined_audio(combined_audio, output_path="combined_output.wav"):
    """結合されたオーディオを一時ファイルとして保存"""
    combined_audio.export(output_path, format="wav")
    return output_path


class AudioPlayer:
    def __init__(self, folder="outputs", gap_seconds=3):
        self.wav_files = get_wav_files(folder)
        if not self.wav_files:
            print("警告: 指定されたフォルダにWAVファイルが見つかりません")
            return
            
        print(f"{len(self.wav_files)}個のWAVファイルを見つけました。結合しています...")
        self.combined_audio, self.file_positions = combine_wav_files(self.wav_files, gap_seconds)
        
        # 一時ファイルに保存
        self.temp_file = tempfile.NamedTemporaryFile(suffix='.wav', delete=False)
        self.temp_file.close()
        self.output_path = save_combined_audio(self.combined_audio, self.temp_file.name)
        
        # 再生状態を追跡
        self.playing = False
        self.play_obj = None
        self.current_position = 0
        self.current_file_name = ""
        
        # ウィジェットの設定
        self.setup_widgets()
        
    def setup_widgets(self):
        """UIウィジェットを作成"""
        self.play_button = widgets.Button(
            description='再生',
            disabled=False,
            button_style='success',
            tooltip='クリックして再生/一時停止',
            icon='play'
        )
        self.play_button.on_click(self.toggle_play)
        
        self.stop_button = widgets.Button(
            description='停止',
            disabled=False,
            button_style='danger',
            tooltip='クリックして停止',
            icon='stop'
        )
        self.stop_button.on_click(self.stop)
        
        self.position_slider = widgets.FloatSlider(
            value=0,
            min=0,
            max=len(self.combined_audio) / 1000.0,
            step=0.1,
            description='位置:',
            disabled=False,
            continuous_update=False,
            orientation='horizontal',
            readout=True,
            readout_format='.1f',
        )
        self.position_slider.observe(self.on_position_change, names='value')
        
        self.file_label = widgets.Label(value="再生準備完了")
        
        self.progress_thread = None
        
    def get_current_file(self, position):
        """現在の位置から再生中のファイル名を取得"""
        for file_info in self.file_positions:
            if file_info['start'] <= position < file_info['end']:
                return file_info['file']
        return "不明なファイル"
    
    def update_progress(self):
        """再生中の進行状況を更新するスレッド"""
        while self.playing:
            if not HAVE_SIMPLEAUDIO or self.play_obj is None:
                break
                
            if not self.play_obj.is_playing():
                # 再生完了した場合
                self.playing = False
                self.play_button.description = '再生'
                self.play_button.icon = 'play'
                self.file_label.value = "再生完了"
                break
                
            # 位置を更新（近似）
            elapsed = time.time() - self.start_time
            self.current_position = self.start_position + elapsed
            
            if self.current_position >= len(self.combined_audio) / 1000.0:
                self.current_position = len(self.combined_audio) / 1000.0
                self.playing = False
                
            # UIを更新（スライダーと現在のファイル名）
            self.position_slider.value = self.current_position
            self.current_file_name = self.get_current_file(self.current_position)
            self.file_label.value = f"再生中: {self.current_file_name}"
            
            time.sleep(0.1)
    
    def toggle_play(self, b):
        """再生と一時停止を切り替え"""
        if self.playing:
            self.pause()
        else:
            self.play()
    
    def play(self):
        """オーディオの再生を開始/再開"""
        if self.playing:
            return
            
        self.playing = True
        self.play_button.description = '一時停止'
        self.play_button.icon = 'pause'
        
        # 現在の位置から再生を開始
        self.start_position = self.position_slider.value
        self.start_time = time.time()
        
        # 再生を開始
        if HAVE_SIMPLEAUDIO:
            # SimpleAudioを使用して指定位置から再生
            wav_obj = self._create_wav_obj_from_position(self.start_position)
            if wav_obj:
                self.play_obj = wav_obj.play()
                
                # 進行状況の更新スレッドを開始
                if self.progress_thread is None or not self.progress_thread.is_alive():
                    self.progress_thread = Thread(target=self.update_progress)
                    self.progress_thread.daemon = True
                    self.progress_thread.start()
        else:
            # SimpleAudioがない場合の代替策（制限あり）
            self.file_label.value = "SimpleAudioがインストールされていないため、再生位置の制御が制限されます"
            display(Audio(self.output_path, autoplay=True))
    
    def _create_wav_obj_from_position(self, position_seconds):
        """指定位置からWAVオブジェクトを作成"""
        try:
            with wave.open(self.output_path, 'rb') as wav_file:
                frame_rate = wav_file.getframerate()
                n_channels = wav_file.getnchannels()
                sample_width = wav_file.getsampwidth()
                
                # フレーム位置を計算
                start_frame = int(position_seconds * frame_rate)
                
                # フレーム位置に移動
                wav_file.setpos(start_frame)
                
                # 残りのフレームを読み込む
                frames = wav_file.readframes(wav_file.getnframes() - start_frame)
                
                # 新しいWAVオブジェクトを作成
                return sa.WaveObject(frames, n_channels, sample_width, frame_rate)
        except Exception as e:
            print(f"再生エラー: {e}")
            return None
    
    def pause(self):
        """再生を一時停止"""
        if not self.playing:
            return
            
        self.playing = False
        self.play_button.description = '再生'
        self.play_button.icon = 'play'
        
        if HAVE_SIMPLEAUDIO and self.play_obj:
            self.play_obj.stop()
    
    def stop(self, b=None):
        """再生を停止して最初に戻る"""
        self.pause()
        self.position_slider.value = 0
        self.current_position = 0
        self.file_label.value = "停止しました"
    
    def on_position_change(self, change):
        """スライダーが変更されたときの処理"""
        if not self.playing:
            # 再生中でなければファイル名だけを更新
            self.current_position = change['new']
            self.current_file_name = self.get_current_file(self.current_position)
            self.file_label.value = f"準備完了: {self.current_file_name}"
        else:
            # 再生中の場合は再生位置を更新
            self.pause()
            self.current_position = change['new']
            self.play()
    
    def display(self):
        """プレーヤーウィジェットを表示"""
        controls = widgets.HBox([self.play_button, self.stop_button])
        display(widgets.VBox([
            self.file_label,
            self.position_slider,
            controls
        ]))
    
    def __del__(self):
        """クリーンアップ"""
        if hasattr(self, 'temp_file') and os.path.exists(self.temp_file.name):
            try:
                os.unlink(self.temp_file.name)
            except:
                pass


def create_audio_player(folder="outputs", gap_seconds=3):
    """オーディオプレーヤーを作成して表示"""
    player = AudioPlayer(folder, gap_seconds)
    player.display()
    return player