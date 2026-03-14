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

class AudioCaptureManager {
    private var audioRecord: AudioRecord? = null
    private var isRecording = false

    private val sampleRate = 16000
    private val channelConfig = AudioFormat.CHANNEL_IN_MONO
    private val audioFormat = AudioFormat.ENCODING_PCM_16BIT
    private val SILENCE_THRESHOLD = 500.0

    // 1. Инициализираме HTTP клиента
    private val client = OkHttpClient()

    // ВАЖНО: Тук ще сложите IP адреса на лаптопа на бекенд човека (напр. 192.168.1.5:8000)
    // Засега слагаме локалния хост на емулатора
    private val BACKEND_URL = "http://10.108.6.198/:8000/predict"
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

    // 3. Функцията, която опакова аудиото и го праща през Интернет
    private fun sendChunkToBackend(shortArray: ShortArray) {
        // Превръщаме числата (Short) в сурови байтове (ByteArray), които сървърът разбира
        val byteBuffer = ByteBuffer.allocate(shortArray.size * 2)
        byteBuffer.order(ByteOrder.LITTLE_ENDIAN)
        byteBuffer.asShortBuffer().put(shortArray)
        val byteArray = byteBuffer.array()

        // Опаковаме ги в заявка
        val requestBody = RequestBody.create("application/octet-stream".toMediaTypeOrNull(), byteArray)
        val request = Request.Builder()
            .url(BACKEND_URL)
            .post(requestBody)
            .build()

        // Изпращаме заявката асинхронно (за да не блокираме микрофона)
        client.newCall(request).enqueue(object : Callback {
            override fun onFailure(call: Call, e: IOException) {
                Log.e("AudioPipeline", "Грешка при връзка със сървъра: ${e.message}")
            }

            override fun onResponse(call: Call, response: Response) {
                val responseBody = response.body?.string()
                Log.d("AudioPipeline", "Отговор от сървъра: $responseBody")
                // TODO: Утре ще вържем този отговор да променя текста на екрана!
            }
        })
    }
}