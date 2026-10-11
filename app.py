#!/usr/bin/env python3
"""
Guitar Learning App — PySide6  (Professional Edition)
Interactive fretboard, chord library, scale patterns, quiz & practice tools.
Karplus-Strong synthesis, strummed chords, refined dark-amber theme.
"""

import sys, math, random, struct, wave, tempfile, os, shutil
from collections import OrderedDict

from PySide6.QtWidgets import (
    QApplication, QMainWindow, QWidget, QVBoxLayout, QHBoxLayout,
    QGridLayout, QTabWidget, QGroupBox, QLabel, QPushButton, QComboBox,
    QSpinBox, QCheckBox, QScrollArea, QSizePolicy, QFrame
)
from PySide6.QtCore import Qt, QTimer, Signal, QRectF, QPointF, QUrl
from PySide6.QtGui import (
    QPainter, QPen, QBrush, QColor, QFont, QLinearGradient,
    QRadialGradient, QConicalGradient, QPainterPath
)

try:
    from PySide6.QtMultimedia import QMediaPlayer, QAudioOutput
    HAS_AUDIO = True
except ImportError:
    HAS_AUDIO = False

# ── Music Theory Data ────────────────────────────────────────────────────────

NOTES = ['C', 'C#', 'D', 'D#', 'E', 'F', 'F#', 'G', 'G#', 'A', 'A#', 'B']

STRING_OPEN   = [4, 9, 2, 7, 11, 4]
STRING_LABELS = ['E', 'A', 'D', 'G', 'B', 'e']
OPEN_FREQS    = [82.41, 110.00, 146.83, 196.00, 246.94, 329.63]

# Per-string synthesis parameters: lower strings ring longer & are darker
STRING_DECAY      = [0.9992, 0.9988, 0.9983, 0.9978, 0.9973, 0.9966]
STRING_BRIGHTNESS = [0.35, 0.40, 0.50, 0.60, 0.70, 0.80]

FRET_MARKERS = {3: True, 5: True, 7: True, 9: True, 12: 'double',
                15: True, 17: True, 19: True, 21: True}

CHORD_DATA = OrderedDict([
    ('C',   {'s': [-1, 3, 2, 0, 1, 0], 'f': [0, 3, 2, 0, 1, 0], 'cat': 'Major'}),
    ('D',   {'s': [-1,-1, 0, 2, 3, 2], 'f': [0, 0, 0, 1, 3, 2], 'cat': 'Major'}),
    ('E',   {'s': [ 0, 2, 2, 1, 0, 0], 'f': [0, 2, 3, 1, 0, 0], 'cat': 'Major'}),
    ('G',   {'s': [ 3, 2, 0, 0, 0, 3], 'f': [2, 1, 0, 0, 0, 3], 'cat': 'Major'}),
    ('A',   {'s': [-1, 0, 2, 2, 2, 0], 'f': [0, 0, 1, 2, 3, 0], 'cat': 'Major'}),
    ('Am',  {'s': [-1, 0, 2, 2, 1, 0], 'f': [0, 0, 2, 3, 1, 0], 'cat': 'Minor'}),
    ('Em',  {'s': [ 0, 2, 2, 0, 0, 0], 'f': [0, 2, 3, 0, 0, 0], 'cat': 'Minor'}),
    ('Dm',  {'s': [-1,-1, 0, 2, 3, 1], 'f': [0, 0, 0, 2, 3, 1], 'cat': 'Minor'}),
    ('F',   {'s': [ 1, 3, 3, 2, 1, 1], 'f': [1, 3, 4, 2, 1, 1], 'cat': 'Barre'}),
    ('Bm',  {'s': [-1, 2, 4, 4, 3, 2], 'f': [0, 1, 3, 4, 2, 1], 'cat': 'Barre'}),
    ('G7',  {'s': [ 3, 2, 0, 0, 0, 1], 'f': [3, 2, 0, 0, 0, 1], 'cat': '7th'}),
    ('C7',  {'s': [-1, 3, 2, 3, 1, 0], 'f': [0, 3, 2, 4, 1, 0], 'cat': '7th'}),
    ('D7',  {'s': [-1,-1, 0, 2, 1, 2], 'f': [0, 0, 0, 2, 1, 3], 'cat': '7th'}),
    ('A7',  {'s': [-1, 0, 2, 0, 2, 0], 'f': [0, 0, 2, 0, 3, 0], 'cat': '7th'}),
    ('E7',  {'s': [ 0, 2, 0, 1, 0, 0], 'f': [0, 2, 0, 1, 0, 0], 'cat': '7th'}),
    ('B7',  {'s': [-1, 2, 1, 2, 0, 2], 'f': [0, 2, 1, 3, 0, 4], 'cat': '7th'}),
])

SCALE_DATA = OrderedDict([
    ('Major (Ionian)',          [0, 2, 4, 5, 7, 9, 11]),
    ('Natural Minor (Aeolian)', [0, 2, 3, 5, 7, 8, 10]),
    ('Pentatonic Major',        [0, 2, 4, 7, 9]),
    ('Pentatonic Minor',        [0, 3, 5, 7, 10]),
    ('Blues',                   [0, 3, 5, 6, 7, 10]),
    ('Dorian',                  [0, 2, 3, 5, 7, 9, 10]),
    ('Mixolydian',              [0, 2, 4, 5, 7, 9, 10]),
    ('Harmonic Minor',          [0, 2, 3, 5, 7, 8, 11]),
    ('Phrygian',                [0, 1, 3, 5, 7, 8, 10]),
    ('Lydian',                  [0, 2, 4, 6, 7, 9, 11]),
    ('Locrian',                 [0, 1, 3, 5, 6, 8, 10]),
])

PROGRESSIONS = [
    ('I – V – vi – IV (Pop)',     ['C', 'G', 'Am', 'F']),
    ('I – vi – IV – V (50s)',     ['C', 'Am', 'F', 'G']),
    ('I – IV – V (Blues)',        ['C', 'F', 'G']),
    ('ii – V – I (Jazz)',         ['Dm', 'G7', 'C']),
    ('I – IV – vi – V',           ['C', 'F', 'Am', 'G']),
    ('vi – IV – I – V (Minor)',   ['Am', 'F', 'C', 'G']),
    ('I – iii – IV – V',          ['C', 'Em', 'F', 'G']),
    ('I – V – IV – V (Rock)',     ['E', 'B7', 'A', 'B7']),
]

INTERVAL_NAMES = ['R', '♭2', '2', '♭3', '3', '4', '♭5', '5', '♭6', '6', '♭7', '7']

SCALE_TIPS = {
    'Major (Ionian)':          'Happy, bright. Foundation of Western music.',
    'Natural Minor (Aeolian)': 'Sad, dark. Rock, metal & ballads.',
    'Pentatonic Major':        'Essential for rock/country soloing — no wrong notes!',
    'Pentatonic Minor':        'The #1 rock & blues soloing scale.',
    'Blues':                   'Minor pentatonic + the "blue note" for extra soul.',
    'Dorian':                  'Jazz/funk — minor with a major 6th.',
    'Mixolydian':              'Rock/blues — major with a flat 7th.',
    'Harmonic Minor':          'Classical, metal, neoclassical — exotic feel.',
    'Phrygian':                'Flamenco & metal — dark with a flat 2nd.',
    'Lydian':                  'Dreamy, floating — major with a sharp 4th.',
    'Locrian':                 'Dissonant, unstable — jazz fusion.',
}

# ── Professional Audio Engine ────────────────────────────────────────────────

class AudioEngine:
    """
    Karplus-Strong plucked-string synthesis + additive body resonance.
    Chord strumming with staggered string timing mixed into a single WAV.
    Separate QMediaPlayer for metronome clicks so they never cut off notes.
    """

    def __init__(self):
        self.player      = None   # main note / chord player
        self.metro_player = None  # dedicated metronome click player
        self.audio_out    = None
        self.metro_out    = None
        self.cache        = {}    # (freq, dur) → wav path
        self.chord_cache  = {}    # chord_name   → wav path
        self.scale_cache  = {}    # scale key    → wav path
        self.click_paths  = {}    # 'accent'|'normal' → wav path
        self.tmp = tempfile.mkdtemp()

        if HAS_AUDIO:
            self.player = QMediaPlayer()
            self.audio_out = QAudioOutput()
            self.player.setAudioOutput(self.audio_out)
            self.audio_out.setVolume(0.55)

            self.metro_player = QMediaPlayer()
            self.metro_out = QAudioOutput()
            self.metro_player.setAudioOutput(self.metro_out)
            self.metro_out.setVolume(0.45)

            # Pre-generate metronome click WAVs
            self._ensure_click_wavs()

    # ── frequency helpers ──

    @staticmethod
    def freq(string_idx, fret):
        return OPEN_FREQS[string_idx] * (2 ** (fret / 12.0))

    # ── Karplus-Strong plucked string ──

    @staticmethod
    def _karplus_strong(frequency, dur, sr=44100, decay=0.996):
        """Physical-model synthesis of a plucked string."""
        N = max(2, int(sr / frequency))
        # Initialise with shaped noise (softened for warmer attack)
        buf = [random.uniform(-1, 1) for _ in range(N)]
        for i in range(1, N):
            buf[i] = 0.5 * buf[i] + 0.5 * buf[i - 1]

        total = int(sr * dur)
        samples = [0.0] * total
        idx = 0
        for i in range(total):
            samples[i] = buf[idx]
            nxt = (idx + 1) % N
            avg = decay * 0.5 * (buf[idx] + buf[nxt])
            buf[idx] = avg
            idx = nxt

        # Add short pick-noise burst for realism
        noise_len = min(int(sr * 0.006), total)
        for i in range(noise_len):
            env = math.exp(-40.0 * i / sr)
            samples[i] += 0.12 * (random.random() * 2 - 1) * env

        # Normalise
        peak = max((abs(s) for s in samples), default=1.0)
        if peak > 0:
            inv = 1.0 / peak
            samples = [s * inv for s in samples]
        return samples

    # ── Additive body resonance ──

    @staticmethod
    def _additive_body(frequency, dur, sr=44100, brightness=0.5):
        """Supplementary harmonic body for richer, fuller tone."""
        total = int(sr * dur)
        harmonics = [(1, 0.55), (2, 0.22), (3, 0.11), (4, 0.05), (5, 0.025)]
        freqs = [frequency * h for h, _ in harmonics]
        amps  = [a * math.exp(-brightness * (h - 1)) for (h, a) in harmonics]
        two_pi = 2.0 * math.pi
        inv_sr = 1.0 / sr

        samples = [0.0] * total
        for i in range(total):
            t = i * inv_sr
            env = math.exp(-2.8 * t / dur)
            if t < 0.003:
                env *= t / 0.003
            val = 0.0
            for f, a in zip(freqs, amps):
                val += a * math.sin(two_pi * f * t)
            samples[i] = val * env

        peak = max((abs(s) for s in samples), default=1.0)
        if peak > 0:
            inv = 1.0 / peak
            samples = [s * inv for s in samples]
        return samples

    # ── Combined note synthesis ──

    def _synthesize(self, frequency, dur, string_idx=0, vol=0.38):
        sr = 44100
        decay = STRING_DECAY[string_idx]
        bright = STRING_BRIGHTNESS[string_idx]
        ks   = self._karplus_strong(frequency, dur, sr, decay)
        body = self._additive_body(frequency, dur, sr, bright)

        n = len(ks)
        out = [0.0] * n
        for i in range(n):
            out[i] = (0.72 * ks[i] + 0.28 * body[i]) * vol

        return out, sr

    # ── WAV I/O ──

    def _write_wav(self, path, samples_float, sr):
        """Convert float [-1,1] samples to 16-bit WAV."""
        data = [int(max(-32767, min(32767, s * 32767))) for s in samples_float]
        with wave.open(path, 'w') as wf:
            wf.setnchannels(1)
            wf.setsampwidth(2)
            wf.setframerate(sr)
            wf.writeframes(struct.pack(f'<{len(data)}h', *data))

    # ── Public: play single note ──

    def play_note(self, string_idx, fret, dur=1.2):
        if not HAS_AUDIO or not self.player:
            return
        f = self.freq(string_idx, fret)
        key = (round(f, 1), dur, string_idx)
        if key in self.cache:
            path = self.cache[key]
        else:
            samples, sr = self._synthesize(f, dur, string_idx)
            path = os.path.join(self.tmp, f"n{f:.1f}_{dur}_{string_idx}.wav")
            self._write_wav(path, samples, sr)
            self.cache[key] = path
        self.player.setSource(QUrl.fromLocalFile(path))
        self.player.play()

    # ── Public: play strummed chord ──

    def play_chord(self, name, dur=2.8):
        if name not in CHORD_DATA or not HAS_AUDIO or not self.player:
            return
        if name in self.chord_cache:
            path = self.chord_cache[name]
        else:
            path = self._generate_chord_wav(name, dur)
            self.chord_cache[name] = path
        self.player.setSource(QUrl.fromLocalFile(path))
        self.player.play()

    def _generate_chord_wav(self, name, dur):
        d = CHORD_DATA[name]
        sr = 44100
        strum_delay = 0.032  # 32 ms between each string
        active = [(s, max(0, d['s'][s])) for s in range(6) if d['s'][s] >= 0]
        total_dur = dur + strum_delay * len(active)
        total_n = int(sr * total_dur)
        mixed = [0.0] * total_n
        vol_per = 0.38 / max(1, len(active) * 0.45)

        for strum_i, (si, fret) in enumerate(active):
            f = self.freq(si, fret)
            ks   = self._karplus_strong(f, dur, sr, STRING_DECAY[si])
            body = self._additive_body(f, dur, sr, STRING_BRIGHTNESS[si])
            offset = int(strum_i * strum_delay * sr)
            note_n = min(len(ks), len(body), total_n - offset)
            for i in range(note_n):
                mixed[offset + i] += vol_per * (0.72 * ks[i] + 0.28 * body[i])

        # Normalise to 0.92
        peak = max((abs(s) for s in mixed), default=1.0)
        if peak > 0:
            s = 0.92 / peak
            mixed = [v * s for v in mixed]

        path = os.path.join(self.tmp, f"chord_{name}.wav")
        self._write_wav(path, mixed, sr)
        return path

    # ── Public: play full scale (single WAV, precise timing) ──

    def play_scale(self, root_idx, intervals, dur_per_note=0.48):
        if not HAS_AUDIO or not self.player:
            return
        key = (root_idx, tuple(intervals))
        if key in self.scale_cache:
            path = self.scale_cache[key]
        else:
            path = self._generate_scale_wav(root_idx, intervals, dur_per_note)
            self.scale_cache[key] = path
        self.player.setSource(QUrl.fromLocalFile(path))
        self.player.play()

    def _generate_scale_wav(self, root_idx, intervals, dur_per_note):
        sr = 44100
        gap = 0.06
        # Find root on high-E string
        si = 5
        base = 0
        for f in range(0, 13):
            if (STRING_OPEN[si] + f) % 12 == root_idx:
                base = f; break

        all_samples = []
        for iv in intervals:
            fret = base + iv
            if fret > 15:
                fret = base + iv - 12  # wrap octave
            f = self.freq(si, min(fret, 15))
            ks   = self._karplus_strong(f, dur_per_note, sr, STRING_DECAY[si])
            body = self._additive_body(f, dur_per_note, sr, STRING_BRIGHTNESS[si])
            for i in range(len(ks)):
                all_samples.append(0.38 * (0.72 * ks[i] + 0.28 * body[i]))
            for _ in range(int(sr * gap)):
                all_samples.append(0.0)

        peak = max((abs(s) for s in all_samples), default=1.0)
        if peak > 0:
            s = 0.9 / peak
            all_samples = [v * s for v in all_samples]

        path = os.path.join(self.tmp, f"scale_{root_idx}_{hash(tuple(intervals))}.wav")
        self._write_wav(path, all_samples, sr)
        return path

    # ── Metronome clicks (separate player) ──

    def _ensure_click_wavs(self):
        sr = 44100
        for accent in (True, False):
            key = 'accent' if accent else 'normal'
            path = os.path.join(self.tmp, f"click_{key}.wav")
            if os.path.exists(path):
                self.click_paths[key] = path
                continue
            freq = 1800 if accent else 1200
            dur = 0.035
            total = int(sr * dur)
            samples = []
            for i in range(total):
                t = i / sr
                env = math.exp(-55.0 * t)
                val = math.sin(2 * math.pi * freq * t) * env
                val += 0.22 * (random.random() * 2 - 1) * math.exp(-90.0 * t)
                samples.append(val * 0.55)
            peak = max((abs(s) for s in samples), default=1.0)
            if peak > 0:
                s = 0.9 / peak
                samples = [v * s for v in samples]
            self._write_wav(path, samples, sr)
            self.click_paths[key] = path

    def play_click(self, accent=False):
        if not HAS_AUDIO or not self.metro_player:
            return
        key = 'accent' if accent else 'normal'
        self.metro_player.setSource(QUrl.fromLocalFile(self.click_paths[key]))
        self.metro_player.play()

    # ── Volume ──

    def set_volume(self, v):
        if self.audio_out:
            self.audio_out.setVolume(v)

    def set_metronome_volume(self, v):
        if self.metro_out:
            self.metro_out.setVolume(v)

    def cleanup(self):
        try:
            shutil.rmtree(self.tmp)
        except Exception:
            pass


# ── Guitar Fretboard Widget ──────────────────────────────────────────────────

class GuitarFretboard(QWidget):
    note_clicked = Signal(int, int)

    def __init__(self, num_frets=15, parent=None):
        super().__init__(parent)
        self.num_frets    = num_frets
        self.show_notes   = True
        self.highlighted  = set()
        self.roots        = set()
        self.root_note_idx = 0
        self.label_mode   = 'note'
        self.hover        = None
        self.LM = 48; self.RM = 20; self.TM = 32; self.BM = 28
        self.setMinimumSize(760, 210)
        self.setMouseTracking(True)

    def note_name(self, s, f): return NOTES[(STRING_OPEN[s] + f) % 12]
    def note_idx(self, s, f):  return (STRING_OPEN[s] + f) % 12

    def _fx(self, fret, w):
        pw = w - self.LM - self.RM
        if fret == 0: return self.LM
        total = sum(1.0 / (1 + 0.03 * i) for i in range(self.num_frets))
        cur   = sum(1.0 / (1 + 0.03 * i) for i in range(fret))
        return self.LM + pw * cur / total

    def _sy(self, s, h):
        ph = h - self.TM - self.BM
        return self.TM + ph * (5 - s) / 5

    def highlight_scale(self, root, intervals):
        self.highlighted.clear(); self.roots.clear()
        self.root_note_idx = root
        sc = {(root + iv) % 12 for iv in intervals}
        for s in range(6):
            for f in range(self.num_frets + 1):
                ni = self.note_idx(s, f)
                if ni in sc:
                    self.highlighted.add((s, f))
                    if ni == root: self.roots.add((s, f))
        self.update()

    def highlight_chord(self, name):
        self.highlighted.clear(); self.roots.clear()
        if name not in CHORD_DATA:
            self.update(); return
        d = CHORD_DATA[name]
        rn = name[:2] if len(name) > 1 and name[1] == '#' else name[0]
        ri = NOTES.index(rn)
        self.root_note_idx = ri
        for s in range(6):
            fret = d['s'][s]
            if fret >= 0:
                self.highlighted.add((s, fret))
                if self.note_idx(s, fret) == ri:
                    self.roots.add((s, fret))
        self.update()

    def clear_highlights(self):
        self.highlighted.clear(); self.roots.clear(); self.update()

    def _pos_to_note(self, pos):
        w, h = self.width(), self.height()
        bs, md = None, 20
        for s in range(6):
            d = abs(pos.y() - self._sy(s, h))
            if d < md: md = d; bs = s
        if bs is None: return None, None
        bf, mxd = None, 999
        ox = self._fx(0, w) - 14
        d = abs(pos.x() - ox)
        if d < mxd: mxd = d; bf = 0
        for f in range(1, self.num_frets + 1):
            nx = (self._fx(f - 1, w) + self._fx(f, w)) / 2
            d = abs(pos.x() - nx)
            if d < mxd: mxd = d; bf = f
        if mxd > 38: return None, None
        return bs, bf

    def mouseMoveEvent(self, e):
        s, f = self._pos_to_note(e.position().toPoint())
        self.hover = (s, f) if s is not None else None
        self.update()

    def mousePressEvent(self, e):
        if e.button() == Qt.LeftButton:
            s, f = self._pos_to_note(e.position().toPoint())
            if s is not None: self.note_clicked.emit(s, f)

    def leaveEvent(self, e):
        self.hover = None; self.update()

    def paintEvent(self, _):
        p = QPainter(self); p.setRenderHint(QPainter.Antialiasing)
        w, h = self.width(), self.height()

        # Background
        bg = QLinearGradient(0, 0, 0, h)
        bg.setColorAt(0, QColor(30, 30, 34)); bg.setColorAt(1, QColor(18, 18, 22))
        p.fillRect(self.rect(), bg)

        # Fretboard wood
        y0 = self._sy(5, h) - 16; y1 = self._sy(0, h) + 16
        fx0 = self._fx(0, w); fxn = self._fx(self.num_frets, w)
        wg = QLinearGradient(0, y0, 0, y1)
        wg.setColorAt(0.0, QColor(120, 72, 28))
        wg.setColorAt(0.3, QColor(155, 100, 45))
        wg.setColorAt(0.5, QColor(170, 115, 55))
        wg.setColorAt(0.7, QColor(155, 100, 45))
        wg.setColorAt(1.0, QColor(120, 72, 28))
        p.fillRect(QRectF(fx0, y0, fxn - fx0, y1 - y0), wg)

        # Subtle grain lines
        p.setPen(QPen(QColor(0, 0, 0, 18), 1))
        for gy in range(int(y0) + 6, int(y1) - 4, 5):
            p.drawLine(QPointF(fx0 + 2, gy), QPointF(fxn - 2, gy))

        # Nut (bone)
        nut_grad = QLinearGradient(fx0 - 5, 0, fx0 + 5, 0)
        nut_grad.setColorAt(0, QColor(220, 218, 200))
        nut_grad.setColorAt(0.5, QColor(245, 242, 230))
        nut_grad.setColorAt(1, QColor(210, 208, 190))
        p.fillRect(QRectF(fx0 - 5, y0, 10, y1 - y0), nut_grad)

        # Frets (metallic)
        for f in range(1, self.num_frets + 1):
            x = self._fx(f, w)
            fg = QLinearGradient(x - 1, 0, x + 2, 0)
            fg.setColorAt(0, QColor(160, 160, 165))
            fg.setColorAt(0.5, QColor(210, 210, 215))
            fg.setColorAt(1, QColor(150, 150, 155))
            p.setPen(Qt.NoPen); p.setBrush(fg)
            p.drawRect(QRectF(x - 1.2, y0 + 3, 2.8, y1 - y0 - 6))

        # Inlay markers (pearl)
        p.setPen(Qt.NoPen)
        my = (y0 + y1) / 2
        for fn, mk in FRET_MARKERS.items():
            if fn > self.num_frets: continue
            mx = (self._fx(fn - 1, w) + self._fx(fn, w)) / 2
            ig = QRadialGradient(mx, my, 7)
            ig.setColorAt(0, QColor(240, 238, 225, 140))
            ig.setColorAt(0.7, QColor(210, 208, 195, 100))
            ig.setColorAt(1, QColor(180, 178, 165, 50))
            p.setBrush(ig)
            if mk == 'double':
                p.drawEllipse(QPointF(mx, my - 18), 6, 6)
                p.drawEllipse(QPointF(mx, my + 18), 6, 6)
            else:
                p.drawEllipse(QPointF(mx, my), 6, 6)

        # Strings (metallic gradient per string)
        for s in range(6):
            y = self._sy(s, h)
            thick = 3.2 - s * 0.45
            sg = QLinearGradient(0, y - thick / 2, 0, y + thick / 2)
            sg.setColorAt(0, QColor(190, 175, 120))
            sg.setColorAt(0.4, QColor(225, 210, 160))
            sg.setColorAt(1, QColor(175, 160, 110))
            p.setPen(QPen(QBrush(sg), thick))
            p.drawLine(QPointF(fx0 - 8, y), QPointF(fxn + 8, y))

        # String labels
        p.setPen(QColor(170, 170, 175))
        p.setFont(QFont('Segoe UI', 9, QFont.Bold))
        for s in range(6):
            p.drawText(QRectF(0, self._sy(s, h) - 10, self.LM - 10, 20),
                       Qt.AlignRight | Qt.AlignVCenter, STRING_LABELS[s])

        # Fret numbers
        p.setPen(QColor(120, 120, 125)); p.setFont(QFont('Segoe UI', 8))
        for f in range(self.num_frets + 1):
            x = self._fx(0, w) if f == 0 else (self._fx(f - 1, w) + self._fx(f, w)) / 2
            p.drawText(QRectF(x - 14, h - self.BM, 28, self.BM), Qt.AlignCenter, str(f))

        # Notes
        for s in range(6):
            for f in range(self.num_frets + 1):
                self._draw_note(p, s, f, w, h)
        p.end()

    def _draw_note(self, p, s, f, w, h):
        hl = (s, f) in self.highlighted
        rt = (s, f) in self.roots
        hv = self.hover == (s, f)

        if f == 0 and not hl and not hv:
            return

        x = (self._fx(0, w) - 14) if f == 0 else (self._fx(f - 1, w) + self._fx(f, w)) / 2
        y = self._sy(s, h)
        r = 12 if hl else 10

        if hl:
            # Glow
            if rt:
                glow = QRadialGradient(x, y, r + 8)
                glow.setColorAt(0, QColor(239, 68, 68, 50))
                glow.setColorAt(1, QColor(239, 68, 68, 0))
                p.setPen(Qt.NoPen); p.setBrush(glow)
                p.drawEllipse(QPointF(x, y), r + 8, r + 8)
                col = QColor(239, 68, 68, 230)
            else:
                glow = QRadialGradient(x, y, r + 6)
                glow.setColorAt(0, QColor(20, 184, 166, 40))
                glow.setColorAt(1, QColor(20, 184, 166, 0))
                p.setPen(Qt.NoPen); p.setBrush(glow)
                p.drawEllipse(QPointF(x, y), r + 6, r + 6)
                col = QColor(20, 184, 166, 210)

            ng = QRadialGradient(x - 2, y - 2, r)
            ng.setColorAt(0, col.lighter(130))
            ng.setColorAt(1, col)
            p.setPen(Qt.NoPen); p.setBrush(ng)
            p.drawEllipse(QPointF(x, y), r, r)

        elif hv:
            p.setPen(Qt.NoPen)
            p.setBrush(QColor(90, 90, 95, 170))
            p.drawEllipse(QPointF(x, y), r, r)
        elif self.show_notes:
            p.setPen(Qt.NoPen)
            p.setBrush(QColor(70, 70, 75, 60))
            p.drawEllipse(QPointF(x, y), 7, 7)

        if self.label_mode == 'none':
            return
        if hl or hv:
            if self.label_mode == 'interval' and hl:
                iv = (self.note_idx(s, f) - self.root_note_idx) % 12
                lbl = INTERVAL_NAMES[iv]
            else:
                lbl = self.note_name(s, f)
            p.setPen(QColor(255, 255, 255))
            p.setFont(QFont('Segoe UI', 7, QFont.Bold))
            p.drawText(QRectF(x - r, y - r, 2 * r, 2 * r), Qt.AlignCenter, lbl)


# ── Chord Diagram Widget ─────────────────────────────────────────────────────

class ChordDiagram(QWidget):
    def __init__(self, name=None, parent=None):
        super().__init__(parent)
        self._name = name
        self._data = CHORD_DATA.get(name)
        self.setMinimumSize(145, 195)
        self.setMaximumSize(175, 225)

    def set_chord(self, name):
        self._name = name; self._data = CHORD_DATA.get(name); self.update()

    def paintEvent(self, _):
        p = QPainter(self); p.setRenderHint(QPainter.Antialiasing)
        w, h = self.width(), self.height()
        if not self._data: p.end(); return

        d = self._data; strs = d['s']; fing = d['f']

        ml, mr, mt, mb = 30, 30, 44, 32
        dw = w - ml - mr; dh = h - mt - mb
        nf = 5; ss = dw / 5; fs = dh / nf

        # Background with warm cream
        bg = QRadialGradient(w / 2, h / 2, max(w, h) / 2)
        bg.setColorAt(0, QColor(255, 252, 242))
        bg.setColorAt(1, QColor(240, 236, 220))
        p.fillRect(self.rect(), bg)

        # Subtle border
        p.setPen(QPen(QColor(200, 195, 180), 1))
        p.setBrush(Qt.NoBrush)
        p.drawRoundedRect(self.rect().adjusted(1, 1, -2, -2), 8, 8)

        # Name
        p.setPen(QColor(35, 35, 35))
        p.setFont(QFont('Segoe UI', 15, QFont.Bold))
        p.drawText(QRectF(0, 0, w, 28), Qt.AlignCenter, self._name)

        # Category tag
        cat = d.get('cat', '')
        cat_colors = {'Major': QColor(22, 163, 74), 'Minor': QColor(37, 99, 235),
                      'Barre': QColor(217, 119, 6), '7th': QColor(147, 51, 234)}
        tag_col = cat_colors.get(cat, QColor(100, 100, 100))
        p.setFont(QFont('Segoe UI', 7, QFont.Bold))
        p.setPen(Qt.NoPen); p.setBrush(tag_col)
        tag_w = p.fontMetrics().horizontalAdvance(cat) + 10
        p.drawRoundedRect(QRectF((w - tag_w) / 2, 25, tag_w, 14), 4, 4)
        p.setPen(QColor(255, 255, 255))
        p.drawText(QRectF((w - tag_w) / 2, 25, tag_w, 14), Qt.AlignCenter, cat)

        # Nut
        nut_g = QLinearGradient(ml, mt - 2, ml, mt + 4)
        nut_g.setColorAt(0, QColor(80, 80, 80))
        nut_g.setColorAt(1, QColor(50, 50, 50))
        p.setPen(Qt.NoPen); p.setBrush(nut_g)
        p.drawRect(QRectF(ml - 1, mt - 2, dw + 2, 5))

        # Frets
        p.setPen(QPen(QColor(170, 165, 155), 1))
        for i in range(1, nf + 1):
            y = mt + i * fs
            p.drawLine(QPointF(ml, y), QPointF(ml + dw, y))

        # Strings
        for i in range(6):
            x = ml + i * ss
            thick = 2.2 - i * 0.25
            p.setPen(QPen(QColor(160, 150, 130), thick))
            p.drawLine(QPointF(x, mt), QPointF(x, mt + nf * fs))

        # Open / muted
        for i in range(6):
            x = ml + i * ss; y = mt - 14
            v = strs[i]
            if v == -1:
                p.setPen(QPen(QColor(200, 50, 50), 2))
                p.drawLine(QPointF(x - 5, y - 5), QPointF(x + 5, y + 5))
                p.drawLine(QPointF(x - 5, y + 5), QPointF(x + 5, y - 5))
            elif v == 0:
                p.setPen(QPen(QColor(34, 150, 50), 2)); p.setBrush(Qt.NoBrush)
                p.drawEllipse(QPointF(x, y), 6, 6)

        # Finger dots with shadow
        for i in range(6):
            v = strs[i]; fn = fing[i]
            if v > 0:
                x = ml + i * ss
                y = mt + (v - 0.5) * fs
                # Shadow
                p.setPen(Qt.NoPen)
                p.setBrush(QColor(0, 0, 0, 35))
                p.drawEllipse(QPointF(x + 1, y + 1), 9, 9)
                # Dot gradient
                dg = QRadialGradient(x - 2, y - 2, 9)
                dg.setColorAt(0, QColor(55, 140, 200))
                dg.setColorAt(1, QColor(30, 100, 170))
                p.setBrush(dg)
                p.drawEllipse(QPointF(x, y), 9, 9)
                if fn > 0:
                    p.setPen(QColor(255, 255, 255))
                    p.setFont(QFont('Segoe UI', 8, QFont.Bold))
                    p.drawText(QRectF(x - 9, y - 9, 18, 18), Qt.AlignCenter, str(fn))

        # String labels
        p.setPen(QColor(130, 125, 115)); p.setFont(QFont('Segoe UI', 7))
        for i in range(6):
            x = ml + i * ss
            p.drawText(QRectF(x - 10, h - mb + 6, 20, 14), Qt.AlignCenter, STRING_LABELS[i])

        p.end()


# ── Metronome Widget ─────────────────────────────────────────────────────────

class MetronomeWidget(QWidget):
    beat = Signal(int)

    def __init__(self, parent=None):
        super().__init__(parent)
        self.bpm = 80; self.bpb = 4; self.cur = 0; self.running = False
        self.timer = QTimer(self); self.timer.timeout.connect(self._tick)
        self.setMinimumSize(220, 75); self.setMaximumHeight(95)

    def start(self):
        self.running = True; self.cur = 0
        self.timer.start(60000 // self.bpm); self.update()

    def stop(self):
        self.running = False; self.timer.stop(); self.cur = 0; self.update()

    def set_bpm(self, b):
        self.bpm = b
        if self.running: self.timer.setInterval(60000 // b)

    def _tick(self):
        self.cur = self.cur % self.bpb + 1
        self.beat.emit(self.cur); self.update()

    def paintEvent(self, _):
        p = QPainter(self); p.setRenderHint(QPainter.Antialiasing)
        w, h = self.width(), self.height()

        bg = QLinearGradient(0, 0, 0, h)
        bg.setColorAt(0, QColor(30, 30, 35)); bg.setColorAt(1, QColor(22, 22, 26))
        p.fillRect(self.rect(), bg)
        p.setPen(QPen(QColor(50, 50, 55), 1)); p.setBrush(Qt.NoBrush)
        p.drawRoundedRect(self.rect().adjusted(1, 1, -2, -2), 6, 6)

        sz = 20; gap = 14
        tw = self.bpb * (sz + gap) - gap; sx = (w - tw) / 2
        for i in range(self.bpb):
            x = sx + i * (sz + gap); y = (h - sz - 16) / 2
            if self.running and i + 1 == self.cur:
                is_down = (i == 0)
                col = QColor(245, 158, 11) if is_down else QColor(20, 184, 166)
                # Glow
                glow = QRadialGradient(x + sz / 2, y + sz / 2, sz + 6)
                glow.setColorAt(0, QColor(col.red(), col.green(), col.blue(), 60))
                glow.setColorAt(1, QColor(col.red(), col.green(), col.blue(), 0))
                p.setPen(Qt.NoPen); p.setBrush(glow)
                p.drawEllipse(QRectF(x - 6, y - 6, sz + 12, sz + 12))
                # Beat circle
                rg = QRadialGradient(x + sz / 2 - 2, y + sz / 2 - 2, sz / 2 + 2)
                rg.setColorAt(0, col.lighter(120)); rg.setColorAt(1, col)
                p.setBrush(rg)
                p.drawEllipse(QRectF(x - 3, y - 3, sz + 6, sz + 6))
            else:
                p.setBrush(QColor(55, 55, 60))
                p.setPen(QPen(QColor(80, 80, 85), 1))
                p.drawEllipse(QRectF(x, y, sz, sz))
            p.setPen(QColor(220, 220, 225))
            p.setFont(QFont('Segoe UI', 8, QFont.Bold))
            p.drawText(QRectF(x - 3, y - 3, sz + 6, sz + 6), Qt.AlignCenter, str(i + 1))

        p.setPen(QColor(150, 150, 155)); p.setFont(QFont('Segoe UI', 9))
        p.drawText(QRectF(0, h - 18, w, 16), Qt.AlignCenter, f"♩ = {self.bpm} BPM")
        p.end()


# ── Separator helper ─────────────────────────────────────────────────────────

def _hsep():
    """Horizontal line separator."""
    line = QFrame()
    line.setFrameShape(QFrame.HLine)
    line.setStyleSheet("background:#35353d; max-height:1px; margin:4px 0;")
    return line


# ── Fretboard Tab ────────────────────────────────────────────────────────────

class FretboardTab(QWidget):
    def __init__(self, audio, parent=None):
        super().__init__(parent)
        self.audio = audio
        lay = QVBoxLayout(self); lay.setSpacing(10)

        # Title row
        hdr = QHBoxLayout()
        title = QLabel("Interactive Fretboard")
        title.setFont(QFont('Segoe UI', 20, QFont.Bold))
        title.setStyleSheet("color:#F0F0F0;")
        hdr.addWidget(title)
        hdr.addStretch()
        lay.addLayout(hdr)

        # Controls
        ctrl = QHBoxLayout(); ctrl.setSpacing(12)
        ctrl.addWidget(self._lbl("Display:"))
        self.disp = QComboBox()
        self.disp.addItems(["Note Names", "Intervals", "None"])
        self.disp.currentIndexChanged.connect(self._disp_changed)
        ctrl.addWidget(self.disp)
        self.show_cb = QCheckBox("Show All Notes"); self.show_cb.setChecked(True)
        self.show_cb.stateChanged.connect(
            lambda s: (setattr(self.fb, 'show_notes', bool(s)), self.fb.update()))
        ctrl.addWidget(self.show_cb)
        ctrl.addStretch()
        self.info = QLabel("Click on the fretboard to hear any note")
        self.info.setStyleSheet("color:#14B8A6; font-weight:bold; font-size:13px;")
        ctrl.addWidget(self.info)
        lay.addLayout(ctrl)

        self.fb = GuitarFretboard(15)
        self.fb.note_clicked.connect(self._clicked)
        lay.addWidget(self.fb, 1)

        # Reference table
        ref = QGroupBox("Notes per String (Frets 0–12)")
        gl = QGridLayout(); gl.setSpacing(4)
        for s in range(6):
            gl.addWidget(self._lbl(f"{STRING_LABELS[s]}:"), s, 0)
            txt = "  ".join(
                f"[{NOTES[(STRING_OPEN[s]+f)%12]}]" if f == 0
                else NOTES[(STRING_OPEN[s] + f) % 12]
                for f in range(13))
            lb = QLabel(txt); lb.setFont(QFont('Consolas', 8))
            lb.setStyleSheet("color:#a0a0a8;")
            gl.addWidget(lb, s, 1)
        ref.setLayout(gl)
        lay.addWidget(ref)

    @staticmethod
    def _lbl(text):
        l = QLabel(text); l.setStyleSheet("color:#c0c0c5;"); return l

    def _clicked(self, s, f):
        n = self.fb.note_name(s, f)
        freq = AudioEngine.freq(s, f)
        iv = (self.fb.note_idx(s, f) - self.fb.note_idx(s, 0)) % 12
        self.info.setText(
            f"String {STRING_LABELS[s]} · Fret {f} · {n} · "
            f"{INTERVAL_NAMES[iv]} · {freq:.1f} Hz")
        self.audio.play_note(s, max(0, f), 1.0)

    def _disp_changed(self, idx):
        self.fb.label_mode = ['note', 'interval', 'none'][idx]
        self.fb.update()


# ── Chord Library Tab ────────────────────────────────────────────────────────

class ChordLibraryTab(QWidget):
    def __init__(self, audio, parent=None):
        super().__init__(parent)
        self.audio = audio
        lay = QVBoxLayout(self); lay.setSpacing(10)

        hdr = QHBoxLayout()
        title = QLabel("Chord Library")
        title.setFont(QFont('Segoe UI', 20, QFont.Bold))
        title.setStyleSheet("color:#F0F0F0;")
        hdr.addWidget(title); hdr.addStretch()
        lay.addLayout(hdr)

        ctrl = QHBoxLayout(); ctrl.setSpacing(12)
        ctrl.addWidget(QLabel("Category:"))
        self.cat_cb = QComboBox()
        self.cats = OrderedDict([
            ('All',   list(CHORD_DATA.keys())),
            ('Major', [k for k, v in CHORD_DATA.items() if v['cat'] == 'Major']),
            ('Minor', [k for k, v in CHORD_DATA.items() if v['cat'] == 'Minor']),
            ('Barre', [k for k, v in CHORD_DATA.items() if v['cat'] == 'Barre']),
            ('7th',   [k for k, v in CHORD_DATA.items() if v['cat'] == '7th']),
        ])
        self.cat_cb.addItems(self.cats.keys())
        self.cat_cb.currentTextChanged.connect(self._refresh)
        ctrl.addWidget(self.cat_cb)
        self.count_lbl = QLabel()
        self.count_lbl.setStyleSheet("color:#8a8a92; font-style:italic;")
        ctrl.addWidget(self.count_lbl)
        ctrl.addStretch()
        lay.addLayout(ctrl)

        scroll = QScrollArea()
        scroll.setWidgetResizable(True)
        scroll.setStyleSheet("QScrollArea{border:none;background:transparent;}")
        self.grid_w = QWidget()
        self.grid_l = QGridLayout(self.grid_w)
        self.grid_l.setSpacing(14)
        scroll.setWidget(self.grid_w)
        lay.addWidget(scroll, 1)

        self.fb = GuitarFretboard(15)
        self.fb.setMaximumHeight(195)
        self.fb.note_clicked.connect(lambda s, f: self.audio.play_note(s, max(0, f), 0.9))
        lay.addWidget(self.fb)

        self._refresh('All')

    def _refresh(self, cat):
        while self.grid_l.count():
            item = self.grid_l.takeAt(0)
            if item.widget(): item.widget().deleteLater()

        chords = self.cats.get(cat, list(CHORD_DATA.keys()))
        self.count_lbl.setText(f"({len(chords)} chords)")

        cols = 5
        for idx, name in enumerate(chords):
            container = QWidget()
            vl = QVBoxLayout(container)
            vl.setContentsMargins(6, 6, 6, 6); vl.setSpacing(4)

            diag = ChordDiagram(name)
            vl.addWidget(diag)

            play_btn = QPushButton("▶ Play")
            play_btn.setObjectName("accentBtn")
            play_btn.clicked.connect(lambda checked, n=name: self._play(n))
            vl.addWidget(play_btn)

            fb_btn = QPushButton("Show on Fretboard")
            fb_btn.setObjectName("secondaryBtn")
            fb_btn.clicked.connect(lambda checked, n=name: self.fb.highlight_chord(n))
            vl.addWidget(fb_btn)

            container.setStyleSheet("QWidget{background:#222228; border-radius:10px;}")
            self.grid_l.addWidget(container, idx // cols, idx % cols)

    def _play(self, name):
        self.audio.play_chord(name, 2.8)


# ── Scales Tab ───────────────────────────────────────────────────────────────

class ScalesTab(QWidget):
    def __init__(self, audio, parent=None):
        super().__init__(parent)
        self.audio = audio
        lay = QVBoxLayout(self); lay.setSpacing(10)

        hdr = QHBoxLayout()
        title = QLabel("Scale Explorer")
        title.setFont(QFont('Segoe UI', 20, QFont.Bold))
        title.setStyleSheet("color:#F0F0F0;")
        hdr.addWidget(title); hdr.addStretch()
        lay.addLayout(hdr)

        ctrl = QHBoxLayout(); ctrl.setSpacing(12)
        ctrl.addWidget(QLabel("Root:"))
        self.root_cb = QComboBox()
        self.root_cb.addItems(NOTES)
        self.root_cb.currentIndexChanged.connect(self._refresh)
        ctrl.addWidget(self.root_cb)

        ctrl.addWidget(QLabel("Scale:"))
        self.scale_cb = QComboBox()
        self.scale_cb.addItems(SCALE_DATA.keys())
        self.scale_cb.currentIndexChanged.connect(self._refresh)
        ctrl.addWidget(self.scale_cb)
        ctrl.addStretch()

        self.play_btn = QPushButton("▶ Play Scale")
        self.play_btn.setObjectName("accentBtn")
        self.play_btn.clicked.connect(self._play_scale)
        ctrl.addWidget(self.play_btn)
        lay.addLayout(ctrl)

        self.fb = GuitarFretboard(15)
        self.fb.label_mode = 'interval'
        self.fb.note_clicked.connect(lambda s, f: self.audio.play_note(s, max(0, f), 0.9))
        lay.addWidget(self.fb, 1)

        info_grp = QGroupBox("Scale Notes & Info")
        il = QVBoxLayout()
        self.notes_lbl = QLabel()
        self.notes_lbl.setFont(QFont('Consolas', 12))
        self.notes_lbl.setStyleSheet("color:#14B8A6;")
        il.addWidget(self.notes_lbl)
        self.tip_lbl = QLabel()
        self.tip_lbl.setWordWrap(True)
        self.tip_lbl.setStyleSheet("color:#9a9aa0; font-style:italic;")
        il.addWidget(self.tip_lbl)
        info_grp.setLayout(il)
        lay.addWidget(info_grp)

        self._refresh()

    def _refresh(self):
        ri = self.root_cb.currentIndex()
        sname = self.scale_cb.currentText()
        intervals = SCALE_DATA.get(sname, [])
        self.fb.highlight_scale(ri, intervals)
        self.fb.label_mode = 'interval'; self.fb.update()
        names = [NOTES[(ri + iv) % 12] for iv in intervals]
        full  = [NOTES[(ri + iv) % 12] if iv in intervals else '–' for iv in range(12)]
        self.notes_lbl.setText(f"Notes: {'  '.join(names)}\nFull:  {' '.join(full)}")
        tip = SCALE_TIPS.get(sname, '')
        self.tip_lbl.setText(f"💡 {tip}")

    def _play_scale(self):
        ri = self.root_cb.currentIndex()
        sname = self.scale_cb.currentText()
        intervals = SCALE_DATA.get(sname, [])
        self.audio.play_scale(ri, intervals, 0.48)


# ── Practice Tab ─────────────────────────────────────────────────────────────

class PracticeTab(QWidget):
    def __init__(self, audio, parent=None):
        super().__init__(parent)
        self.audio = audio
        self.quiz_score = 0; self.quiz_total = 0; self.quiz_ans = ''
        self.prog_idx = 0
        lay = QVBoxLayout(self); lay.setSpacing(10)

        hdr = QHBoxLayout()
        title = QLabel("Practice Tools")
        title.setFont(QFont('Segoe UI', 20, QFont.Bold))
        title.setStyleSheet("color:#F0F0F0;")
        hdr.addWidget(title); hdr.addStretch()
        lay.addLayout(hdr)

        # ── Note Quiz ──
        quiz_grp = QGroupBox("Note Quiz")
        ql = QVBoxLayout(); ql.setSpacing(8)

        qctrl = QHBoxLayout()
        self.new_q_btn = QPushButton("🎵 New Question")
        self.new_q_btn.setObjectName("warnBtn")
        self.new_q_btn.clicked.connect(self._new_quiz)
        qctrl.addWidget(self.new_q_btn)
        qctrl.addStretch()
        self.score_lbl = QLabel("Score: 0 / 0")
        self.score_lbl.setStyleSheet("color:#FCD34D; font-weight:bold; font-size:14px;")
        qctrl.addWidget(self.score_lbl)
        ql.addLayout(qctrl)

        self.quiz_q = QLabel("Press 'New Question' to start!")
        self.quiz_q.setFont(QFont('Segoe UI', 20, QFont.Bold))
        self.quiz_q.setStyleSheet("color:#E8E8E8; padding:8px;")
        self.quiz_q.setAlignment(Qt.AlignCenter)
        ql.addWidget(self.quiz_q)

        self.quiz_fb = QLabel("")
        self.quiz_fb.setFont(QFont('Segoe UI', 14, QFont.Bold))
        self.quiz_fb.setAlignment(Qt.AlignCenter)
        ql.addWidget(self.quiz_fb)

        ans_lay = QGridLayout(); ans_lay.setSpacing(6)
        self.ans_btns = []
        for i, n in enumerate(NOTES):
            btn = QPushButton(n)
            btn.setObjectName("noteBtn")
            btn.clicked.connect(lambda checked, note=n: self._check_ans(note))
            ans_lay.addWidget(btn, i // 4, i % 4)
            self.ans_btns.append(btn)
        ql.addLayout(ans_lay)
        quiz_grp.setLayout(ql)
        lay.addWidget(quiz_grp)

        # ── Chord Progression Trainer ──
        prog_grp = QGroupBox("Chord Progression Trainer")
        pl = QVBoxLayout(); pl.setSpacing(8)

        pctrl = QHBoxLayout(); pctrl.setSpacing(12)
        pctrl.addWidget(QLabel("Progression:"))
        self.prog_cb = QComboBox()
        for name, _ in PROGRESSIONS:
            self.prog_cb.addItem(name)
        self.prog_cb.currentIndexChanged.connect(self._prog_changed)
        pctrl.addWidget(self.prog_cb)
        pctrl.addStretch()
        self.prog_play = QPushButton("▶ Play")
        self.prog_play.setObjectName("accentBtn")
        self.prog_play.clicked.connect(self._play_prog)
        pctrl.addWidget(self.prog_play)
        pl.addLayout(pctrl)

        self.prog_display = QLabel("")
        self.prog_display.setAlignment(Qt.AlignCenter)
        self.prog_display.setFont(QFont('Segoe UI', 16, QFont.Bold))
        self.prog_display.setStyleSheet("color:#64B5F6; padding:6px;")
        pl.addWidget(self.prog_display)

        self.chord_row = QHBoxLayout(); self.chord_row.setSpacing(10)
        self.chord_labels = []
        pl.addLayout(self.chord_row)

        self.prog_fb = GuitarFretboard(15)
        self.prog_fb.setMaximumHeight(180)
        self.prog_fb.note_clicked.connect(lambda s, f: self.audio.play_note(s, max(0, f), 0.8))
        pl.addWidget(self.prog_fb)

        prog_grp.setLayout(pl)
        lay.addWidget(prog_grp)

        self._prog_changed(0)
        self._new_quiz()

    # Quiz
    def _new_quiz(self):
        s = random.randint(0, 5); f = random.randint(0, 12)
        n = NOTES[(STRING_OPEN[s] + f) % 12]
        self.quiz_ans = n
        self.quiz_q.setText(f"What note is on string {STRING_LABELS[s]}, fret {f}?")
        self.quiz_fb.setText("")
        for btn in self.ans_btns:
            btn.setProperty("state", "")
            btn.style().unpolish(btn); btn.style().polish(btn)

    def _check_ans(self, note):
        self.quiz_total += 1
        correct = (note == self.quiz_ans)
        if correct:
            self.quiz_score += 1
            self.quiz_fb.setText(f"✅ Correct! It's {self.quiz_ans}")
            self.quiz_fb.setStyleSheet("color:#22C55E; font-weight:bold; font-size:14px;")
        else:
            self.quiz_fb.setText(f"❌ Wrong! The answer was {self.quiz_ans}")
            self.quiz_fb.setStyleSheet("color:#EF4444; font-weight:bold; font-size:14px;")

        for btn in self.ans_btns:
            if btn.text() == self.quiz_ans:
                btn.setProperty("state", "correct")
            elif btn.text() == note and not correct:
                btn.setProperty("state", "wrong")
            else:
                btn.setProperty("state", "")
            btn.style().unpolish(btn); btn.style().polish(btn)

        pct = (self.quiz_score / self.quiz_total * 100) if self.quiz_total else 0
        self.score_lbl.setText(f"Score: {self.quiz_score} / {self.quiz_total}  ({pct:.0f}%)")

    # Progression
    def _prog_changed(self, idx):
        self.prog_idx = idx
        while self.chord_row.count():
            item = self.chord_row.takeAt(0)
            if item.widget(): item.widget().deleteLater()
        self.chord_labels.clear()
        _, chords = PROGRESSIONS[idx]
        self.prog_display.setText(" — ".join(chords))
        for c in chords:
            lbl = QPushButton(c)
            lbl.setObjectName("chordBtn")
            lbl.clicked.connect(lambda checked, ch=c: self._highlight_chord(ch))
            self.chord_row.addWidget(lbl)
            self.chord_labels.append(lbl)
        if chords:
            self.prog_fb.highlight_chord(chords[0])

    def _highlight_chord(self, chord):
        self.audio.play_chord(chord, 2.0)
        self.prog_fb.highlight_chord(chord)
        for lbl in self.chord_labels:
            is_active = (lbl.text() == chord)
            lbl.setProperty("active", is_active)
            lbl.style().unpolish(lbl); lbl.style().polish(lbl)

    def _play_prog(self):
        _, chords = PROGRESSIONS[self.prog_idx]
        self._play_prog_step(chords, 0)

    def _play_prog_step(self, chords, idx):
        if idx >= len(chords): return
        chord = chords[idx]
        self.audio.play_chord(chord, 1.2)
        self.prog_fb.highlight_chord(chord)
        for i, lbl in enumerate(self.chord_labels):
            lbl.setProperty("active", i == idx)
            lbl.style().unpolish(lbl); lbl.style().polish(lbl)
        QTimer.singleShot(1400, lambda: self._play_prog_step(chords, idx + 1))


# ── Main Window ──────────────────────────────────────────────────────────────

class MainWindow(QMainWindow):
    def __init__(self):
        super().__init__()
        self.setWindowTitle("Guitar Learning App")
        self.setMinimumSize(1120, 820)
        self.resize(1220, 870)
        self.audio = AudioEngine()
        self.setStyleSheet(self._theme())

        central = QWidget()
        self.setCentralWidget(central)
        ml = QVBoxLayout(central)
        ml.setContentsMargins(12, 10, 12, 10); ml.setSpacing(8)

        # Header
        hdr = QHBoxLayout(); hdr.setSpacing(14)
        icon = QLabel("🎸"); icon.setFont(QFont('Segoe UI Emoji', 26))
        hdr.addWidget(icon)
        htxt = QLabel("Guitar Learning App")
        htxt.setFont(QFont('Segoe UI', 22, QFont.Bold))
        htxt.setStyleSheet("color:#F0F0F0;")
        hdr.addWidget(htxt)
        hdr.addStretch()

        hdr.addWidget(QLabel("🔊 Volume:"))
        vol = QSpinBox()
        vol.setRange(0, 100); vol.setValue(55); vol.setSuffix("%")
        vol.valueChanged.connect(lambda v: self.audio.set_volume(v / 100.0))
        hdr.addWidget(vol)
        ml.addLayout(hdr)
        ml.addWidget(_hsep())

        # Tabs
        self.tabs = QTabWidget()
        self.tabs.setFont(QFont('Segoe UI', 11))

        self.fretboard_tab = FretboardTab(self.audio)
        self.chord_tab     = ChordLibraryTab(self.audio)
        self.scales_tab    = ScalesTab(self.audio)
        self.practice_tab  = PracticeTab(self.audio)

        self.tabs.addTab(self.fretboard_tab, "🎸  Fretboard")
        self.tabs.addTab(self.chord_tab,     "📖  Chords")
        self.tabs.addTab(self.scales_tab,    "🎵  Scales")
        self.tabs.addTab(self.practice_tab,  "🎯  Practice")
        ml.addWidget(self.tabs, 1)

        # Metronome bar
        metro_grp = QGroupBox("🥁 Metronome")
        metro_lay = QHBoxLayout(metro_grp); metro_lay.setSpacing(14)

        self.metro = MetronomeWidget()
        self.metro.beat.connect(self._metro_beat)
        metro_lay.addWidget(self.metro)

        metro_lay.addWidget(QLabel("BPM:"))
        self.bpm_spin = QSpinBox()
        self.bpm_spin.setRange(30, 300); self.bpm_spin.setValue(80)
        self.bpm_spin.valueChanged.connect(self.metro.set_bpm)
        metro_lay.addWidget(self.bpm_spin)

        metro_lay.addWidget(QLabel("Beats:"))
        self.bpb_spin = QSpinBox()
        self.bpb_spin.setRange(2, 12); self.bpb_spin.setValue(4)
        self.bpb_spin.valueChanged.connect(lambda v: setattr(self.metro, 'bpb', v))
        metro_lay.addWidget(self.bpb_spin)

        self.metro_btn = QPushButton("▶ Start")
        self.metro_btn.setObjectName("accentBtn")
        self.metro_btn.clicked.connect(self._toggle_metro)
        metro_lay.addWidget(self.metro_btn)
        ml.addWidget(metro_grp)

    def _toggle_metro(self):
        if self.metro.running:
            self.metro.stop()
            self.metro_btn.setText("▶ Start")
            self.metro_btn.setObjectName("accentBtn")
        else:
            self.metro.start()
            self.metro_btn.setText("⏹ Stop")
            self.metro_btn.setObjectName("dangerBtn")
        self.metro_btn.style().unpolish(self.metro_btn)
        self.metro_btn.style().polish(self.metro_btn)

    def _metro_beat(self, beat):
        self.audio.play_click(accent=(beat == 1))

    def closeEvent(self, event):
        self.metro.stop()
        self.audio.cleanup()
        super().closeEvent(event)

    @staticmethod
    def _theme():
        return """
        /* ── Global ── */
        QMainWindow, QWidget {
            background-color: #111114;
            color: #e0e0e4;
            font-family: 'Segoe UI', Arial, sans-serif;
        }
        QGroupBox {
            border: 1px solid #2e2e36;
            border-radius: 8px;
            margin-top: 14px;
            padding-top: 18px;
            font-weight: bold;
            color: #9a9aa2;
        }
        QGroupBox::title {
            subcontrol-origin: margin;
            left: 14px;
            padding: 0 8px;
        }

        /* ── Tabs ── */
        QTabWidget::pane {
            border: 1px solid #2a2a32;
            border-radius: 6px;
            background: #111114;
        }
        QTabBar::tab {
            background: #1a1a1f;
            color: #8a8a92;
            padding: 9px 22px;
            border: 1px solid #2a2a32;
            border-bottom: none;
            border-top-left-radius: 8px;
            border-top-right-radius: 8px;
            margin-right: 3px;
        }
        QTabBar::tab:selected {
            background: #222228;
            color: #F59E0B;
            font-weight: bold;
            border-bottom: 2px solid #F59E0B;
        }
        QTabBar::tab:hover:!selected {
            background: #1f1f26;
            color: #c0c0c5;
        }

        /* ── Labels ── */
        QLabel { color: #c8c8cd; }

        /* ── ComboBox ── */
        QComboBox {
            background: #1a1a1f;
            color: #e0e0e4;
            border: 1px solid #3a3a42;
            border-radius: 6px;
            padding: 5px 12px;
            min-width: 130px;
        }
        QComboBox::drop-down { border: none; width: 24px; }
        QComboBox::down-arrow {
            image: none;
            border-left: 5px solid transparent;
            border-right: 5px solid transparent;
            border-top: 6px solid #8a8a92;
        }
        QComboBox QAbstractItemView {
            background: #1a1a1f;
            color: #e0e0e4;
            selection-background-color: #F59E0B;
            selection-color: #111;
            border: 1px solid #3a3a42;
            border-radius: 4px;
        }

        /* ── SpinBox ── */
        QSpinBox {
            background: #1a1a1f;
            color: #e0e0e4;
            border: 1px solid #3a3a42;
            border-radius: 6px;
            padding: 4px 8px;
            min-width: 70px;
        }
        QSpinBox::up-button, QSpinBox::down-button {
            background: #2a2a32;
            border: none;
            width: 18px;
        }
        QSpinBox::up-button:hover, QSpinBox::down-button:hover {
            background: #3a3a42;
        }

        /* ── Default QPushButton ── */
        QPushButton {
            background: #2a2a32;
            color: #d0d0d5;
            border: 1px solid #3a3a42;
            border-radius: 6px;
            padding: 7px 16px;
            font-weight: bold;
        }
        QPushButton:hover { background: #35353d; color: #f0f0f0; }
        QPushButton:pressed { background: #1a1a1f; }

        /* ── Accent button (amber) ── */
        QPushButton#accentBtn {
            background: #B45309;
            color: #fff;
            border: none;
            border-radius: 6px;
            padding: 7px 18px;
            font-weight: bold;
        }
        QPushButton#accentBtn:hover { background: #D97706; }
        QPushButton#accentBtn:pressed { background: #92400E; }

        /* ── Danger button (red) ── */
        QPushButton#dangerBtn {
            background: #B91C1C;
            color: #fff;
            border: none;
            border-radius: 6px;
            padding: 7px 18px;
            font-weight: bold;
        }
        QPushButton#dangerBtn:hover { background: #DC2626; }
        QPushButton#dangerBtn:pressed { background: #991B1B; }

        /* ── Warn button (orange) ── */
        QPushButton#warnBtn {
            background: #C2410C;
            color: #fff;
            border: none;
            border-radius: 6px;
            padding: 8px 22px;
            font-weight: bold;
            font-size: 13px;
        }
        QPushButton#warnBtn:hover { background: #EA580C; }
        QPushButton#warnBtn:pressed { background: #9A3412; }

        /* ── Secondary button ── */
        QPushButton#secondaryBtn {
            background: #1E3A5F;
            color: #93C5FD;
            border: none;
            border-radius: 6px;
            padding: 5px 10px;
            font-size: 11px;
            font-weight: bold;
        }
        QPushButton#secondaryBtn:hover { background: #1E4D8A; }

        /* ── Note answer buttons ── */
        QPushButton#noteBtn {
            background: #1f2937;
            color: #e0e0e4;
            border: 1px solid #374151;
            border-radius: 8px;
            padding: 11px;
            font-weight: bold;
            font-size: 13px;
        }
        QPushButton#noteBtn:hover { background: #374151; }
        QPushButton#noteBtn[state="correct"] {
            background: #166534;
            color: #fff;
            border-color: #22C55E;
        }
        QPushButton#noteBtn[state="wrong"] {
            background: #991B1B;
            color: #fff;
            border-color: #EF4444;
        }

        /* ── Chord progression buttons ── */
        QPushButton#chordBtn {
            background: #1f2937;
            color: #93C5FD;
            border: 2px solid #374151;
            border-radius: 10px;
            padding: 12px 20px;
            font-weight: bold;
            font-size: 15px;
        }
        QPushButton#chordBtn:hover { background: #374151; }
        QPushButton#chordBtn[active="true"] {
            background: #1E3A5F;
            color: #F59E0B;
            border-color: #F59E0B;
        }

        /* ── CheckBox ── */
        QCheckBox { color: #c8c8cd; spacing: 7px; }
        QCheckBox::indicator {
            width: 18px; height: 18px;
            border: 1px solid #4a4a52;
            border-radius: 4px;
            background: #1a1a1f;
        }
        QCheckBox::indicator:checked {
            background: #D97706;
            border-color: #D97706;
        }

        /* ── ScrollBar ── */
        QScrollBar:vertical {
            background: #111114;
            width: 10px;
            border-radius: 5px;
        }
        QScrollBar::handle:vertical {
            background: #3a3a42;
            border-radius: 5px;
            min-height: 30px;
        }
        QScrollBar::handle:vertical:hover { background: #4a4a52; }
        QScrollBar::add-line:vertical, QScrollBar::sub-line:vertical { height: 0; }
        QScrollBar::add-page:vertical, QScrollBar::sub-page:vertical { background: none; }

        QScrollArea { background: transparent; border: none; }
        """


# ── Entry Point ──────────────────────────────────────────────────────────────

def main():
    app = QApplication(sys.argv)
    app.setStyle('Fusion')
    window = MainWindow()
    window.show()
    exit_code = app.exec()
    window.audio.cleanup()
    sys.exit(exit_code)

if __name__ == '__main__':
    main()