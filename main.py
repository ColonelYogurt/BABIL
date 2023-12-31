#!/usr/bin/env python3
import whisper
import os
import numpy as np
import sounddevice as sd
from scipy.io.wavfile import write

English = True
Translate = False
SampleRate = 4100
BlockSize = 30      # Block size in milliseconds
Threshold = 0.1     # Minimum volume threshold to activate listening
Vocals = [50, 1000]  # Frequency range to detect sounds that could be speech
EndBlocks = 40      # Number of blocks to wait before sending to Whisper


class StreamHandler:
    def __init__(self, assist=None):
        if assist == None:
            class fakeAsst():
                running, talking, analyze = True, False, None
            self.asst = fakeAsst()
        else:
            self.asst = assist
        self.running = True
        self.padding = 0
        self.prevblock = self.buffer = np.zeros((0, 1))
        self.fileready = False
        print("\033[96mLoading Whisper Model..\033[0m", end='', flush=True)
        self.model = whisper.load_model('large')
        print("\033[90m Done.\033[0m")

    def callback(self, indata, frames, time, status):

        if not any(indata):
            # if no input, prints red dots
            print('\033[31m.\033[0m', end='', flush=True)

            return

        freq = np.argmax(
            np.abs(np.fft.rfft(indata[:, 0]))) * SampleRate / frames
        if np.sqrt(np.mean(indata**2)) > Threshold and Vocals[0] <= freq <= Vocals[1] and not self.asst.talking:
            print('.', end='', flush=True)
            if self.padding < 1:
                self.buffer = self.prevblock.copy()
            self.buffer = np.concatenate((self.buffer, indata))
            self.padding = EndBlocks
        else:
            self.padding -= 1
            if self.padding > 1:
                self.buffer = np.concatenate((self.buffer, indata))
            # if silence has passed, write to file.
            elif self.padding < 1 < self.buffer.shape[0] > SampleRate:
                self.fileready = True
                write('dictate.wav', SampleRate, self.buffer)
                self.buffer = np.zeros((0, 1))
            # if  not long enough, reset buffer.
            elif self.padding < 1 < self.buffer.shape[0] < SampleRate:
                self.buffer = np.zeros((0, 1))
                print("\033[2K\033[0G", end='', flush=True)
            else:
                self.prevblock = indata.copy()

    def process(self):
        if self.fileready:
            print("\n\033[90mTranscribing..\033[0m")
            result = self.model.transcribe(
                'dictate.wav', fp16=False, language='en' if English else '', task='translate' if Translate else 'transcribe')
            print(f"\033[1A\033[2K\033[0G{result['text']}")
            if self.asst.analyze != None:
                self.asst.analyze(result['text'])
            self.fileready = False

    def listen(self):
        print("\033[32mListening.. \033[37m(Ctrl+C to Quit)\033[0m")
        with sd.InputStream(channels=1, callback=self.callback, blocksize=int(SampleRate * BlockSize / 1000), samplerate=SampleRate):
            while self.running and self.asst.running:
                self.process()


def main():
    try:
        handler = StreamHandler()
        handler.listen()
    except (KeyboardInterrupt, SystemExit):
        pass
    finally:
        print("\n\033[93mQuitting..\033[0m")
        if os.path.exists('dictate.wav'):
            os.remove('dictate.wav')


if __name__ == '__main__':
    main()
