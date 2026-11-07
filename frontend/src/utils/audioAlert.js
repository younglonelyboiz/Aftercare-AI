/**
 * Web Audio API Synthesizer - Hệ thống phát âm thanh cảnh báo y tế chuẩn quốc tế
 * Không phụ thuộc vào file MP3 tĩnh ngoài, hoạt động 100% trên mọi trình duyệt.
 */

class MedicalAudioAlert {
  constructor() {
    this.audioCtx = null;
    this.intervalId = null;
    this.isPlaying = false;
    this.isMuted = false;
  }

  initContext() {
    if (!this.audioCtx) {
      const AudioContext = window.AudioContext || window.webkitAudioContext;
      if (AudioContext) {
        this.audioCtx = new AudioContext();
      }
    }
    if (this.audioCtx && this.audioCtx.state === 'suspended') {
      this.audioCtx.resume();
    }
  }

  /**
   * Phát chuỗi xung âm thanh kép (Dual-tone Siren: 880Hz / 660Hz) chuẩn ICU cho P0_CRITICAL
   */
  startP0Siren() {
    if (this.isMuted || this.isPlaying) return;
    this.initContext();
    if (!this.audioCtx) return;

    this.isPlaying = true;
    let high = true;

    const playTone = () => {
      if (!this.isPlaying || this.isMuted) return;

      try {
        const osc = this.audioCtx.createOscillator();
        const gain = this.audioCtx.createGain();

        osc.type = 'sawtooth'; // Âm thanh sắc nét, xuyên thấu tiếng ồn
        osc.frequency.setValueAtTime(high ? 880 : 660, this.audioCtx.currentTime); // A5 / E5

        // Điều chỉnh âm lượng an toàn không gây chói tai
        gain.gain.setValueAtTime(0.25, this.audioCtx.currentTime);
        gain.gain.exponentialRampToValueAtTime(0.01, this.audioCtx.currentTime + 0.22);

        osc.connect(gain);
        gain.connect(this.audioCtx.destination);

        osc.start();
        osc.stop(this.audioCtx.currentTime + 0.22);
      } catch (err) {
        console.warn('Web Audio Play error:', err);
      }

      high = !high;
    };

    // Phát ngay lập tức tiếng đầu tiên
    playTone();
    // Lặp lại chu kỳ mỗi 250ms
    this.intervalId = setInterval(playTone, 250);
  }

  /**
   * Phát một tiếng Beep cảnh báo đơn cho P1 (Vùng Vàng / Quá hạn)
   */
  playWarningBeep() {
    if (this.isMuted) return;
    this.initContext();
    if (!this.audioCtx) return;

    try {
      const osc = this.audioCtx.createOscillator();
      const gain = this.audioCtx.createGain();

      osc.type = 'sine';
      osc.frequency.setValueAtTime(587.33, this.audioCtx.currentTime); // D5

      gain.gain.setValueAtTime(0.2, this.audioCtx.currentTime);
      gain.gain.exponentialRampToValueAtTime(0.01, this.audioCtx.currentTime + 0.4);

      osc.connect(gain);
      gain.connect(this.audioCtx.destination);

      osc.start();
      osc.stop(this.audioCtx.currentTime + 0.4);
    } catch (err) {
      console.warn('Warning beep error:', err);
    }
  }

  stop() {
    this.isPlaying = false;
    if (this.intervalId) {
      clearInterval(this.intervalId);
      this.intervalId = null;
    }
  }

  toggleMute() {
    this.isMuted = !this.isMuted;
    if (this.isMuted) {
      this.stop();
    }
    return this.isMuted;
  }
}

export const medicalAudioAlert = new MedicalAudioAlert();

