package com.example.audiopipelinetest

import android.annotation.SuppressLint
import android.media.AudioFormat
import android.media.AudioRecord
import android.media.MediaRecorder
import android.util.Log
import okhttp3.*
import okhttp3.MediaType.Companion.toMediaTypeOrNull
import java.io.IOException
import java.nio.ByteBuffer
import java.nio.ByteOrder
import kotlin.math.sqrt
import okhttp3.MultipartBody


class AudioCaptureManager {
    private var audioRecord: AudioRecord? = null
    private var isRecording = false

    private val sampleRate = 16000
    private val channelConfig = AudioFormat.CHANNEL_IN_MONO
    private val audioFormat = AudioFormat.ENCODING_PCM_16BIT
    private val SILENCE_THRESHOLD = 500.0

    private val client = OkHttpClient()

    private val BACKEND_URL = "http://10.108.6.198:8000/predict"
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
                    val volume = calculateRMS(chunkBuffer)

                    if (volume > SILENCE_THRESHOLD) {
                        Log.d("AudioPipeline", "🗣 ГЛАС ЗАСЕЧЕН! Сила: ${volume.toInt()}. Пращам към сървъра...")

                        // 2. Викаме функцията за изпращане
                        sendChunkToBackend(chunkBuffer)

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

    private fun calculateRMS(buffer: ShortArray): Double {
        var sum = 0.0
        for (sample in buffer) {
            sum += (sample * sample).toDouble()
        }
        val mean = sum / buffer.size
        return sqrt(mean)
    }

    private fun sendChunkToBackend(shortArray: ShortArray) {
        // Превръщаме PCM в истински WAV файл
        val pcmBytes = ByteBuffer.allocate(shortArray.size * 2)
        pcmBytes.order(ByteOrder.LITTLE_ENDIAN)
        pcmBytes.asShortBuffer().put(shortArray)
        val pcmArray = pcmBytes.array()

        val wavBytes = addWavHeader(pcmArray, sampleRate)

        val requestBody = MultipartBody.Builder()
            .setType(MultipartBody.FORM)
            .addFormDataPart(
                "file",           // името което FastAPI очаква
                "audio.wav",
                RequestBody.create("audio/wav".toMediaTypeOrNull(), wavBytes)
            )
            .build()

        val request = Request.Builder()
            .url(BACKEND_URL)
            .post(requestBody)
            .build()

        client.newCall(request).enqueue(object : Callback {
            override fun onFailure(call: Call, e: IOException) {
                Log.e("AudioPipeline", "Грешка: ${e.message}")
            }
            override fun onResponse(call: Call, response: Response) {
                Log.d("AudioPipeline", "Отговор: ${response.body?.string()}")
            }
        })
    }

    private fun addWavHeader(pcmData: ByteArray, sampleRate: Int): ByteArray {
        val totalDataLen = pcmData.size + 36
        val byteRate = sampleRate * 2 // mono * 16bit
        val buffer = ByteBuffer.allocate(44 + pcmData.size)
        buffer.order(ByteOrder.LITTLE_ENDIAN)

        buffer.put("RIFF".toByteArray())
        buffer.putInt(totalDataLen)
        buffer.put("WAVE".toByteArray())
        buffer.put("fmt ".toByteArray())
        buffer.putInt(16)
        buffer.putShort(1)  // PCM
        buffer.putShort(1)  // Mono
        buffer.putInt(sampleRate)
        buffer.putInt(byteRate)
        buffer.putShort(2)  // block align
        buffer.putShort(16) // bits per sample
        buffer.put("data".toByteArray())
        buffer.putInt(pcmData.size)
        buffer.put(pcmData)

        return buffer.array()
    }
}