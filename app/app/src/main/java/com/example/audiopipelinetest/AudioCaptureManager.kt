package com.example.audiopipelinetest

import android.annotation.SuppressLint
import android.media.AudioFormat
import android.media.AudioRecord
import android.media.MediaRecorder
import android.util.Log
import kotlin.math.sqrt

class AudioCaptureManager {
    private var audioRecord: AudioRecord? = null
    private var isRecording = false

    // Настройките за AI (16 kHz, Mono, 16-bit PCM)
    private val sampleRate = 16000
    private val channelConfig = AudioFormat.CHANNEL_IN_MONO
    private val audioFormat = AudioFormat.ENCODING_PCM_16BIT

    // ПРАГ ЗА ТИШИНА: Ако силата на звука е под това число, го броим за тишина.
    // Може да се наложи да го промениш (напр. 300 или 800) според микрофона.
    private val SILENCE_THRESHOLD = 500.0

    @SuppressLint("MissingPermission")
    fun startRecording() {
        val minBufferSize = AudioRecord.getMinBufferSize(sampleRate, channelConfig, audioFormat)

        audioRecord = AudioRecord(
            MediaRecorder.AudioSource.MIC,
            sampleRate,
            channelConfig,
            audioFormat,
            minBufferSize
        )

        audioRecord?.startRecording()
        isRecording = true
        Log.d("AudioPipeline", "Микрофонът е пуснат!")

        Thread {
            val chunkBuffer = ShortArray(16000)

            while (isRecording) {
                val readResult = audioRecord?.read(chunkBuffer, 0, chunkBuffer.size) ?: 0

                if (readResult > 0) {
                    // 1. Изчисляваме силата на звука в този 1-секунден chunk
                    val volume = calculateRMS(chunkBuffer)

                    // 2. Проверяваме дали е тишина или реч
                    if (volume > SILENCE_THRESHOLD) {
                        Log.d("AudioPipeline", "🗣 ГЛАС ЗАСЕЧЕН! Сила: ${volume.toInt()}. Готов за AI!")

                        // TODO: Тук ще опаковаме chunkBuffer-а и ще го пратим към бекенда
                    } else {
                        Log.d("AudioPipeline", "🤫 Тишина... Сила: ${volume.toInt()}. Пропускаме.")
                    }
                }
            }
        }.start()
    }

    fun stopRecording() {
        isRecording = false
        audioRecord?.stop()
        audioRecord?.release()
        audioRecord = null
        Log.d("AudioPipeline", "Микрофонът е спрян.")
    }

    // Математическата функция за изчисляване на силата на звука
    private fun calculateRMS(buffer: ShortArray): Double {
        var sum = 0.0
        for (sample in buffer) {
            sum += (sample * sample).toDouble()
        }
        val mean = sum / buffer.size
        return sqrt(mean)
    }
}