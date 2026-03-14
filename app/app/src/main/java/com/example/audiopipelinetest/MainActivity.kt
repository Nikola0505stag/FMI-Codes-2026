package com.example.audiopipelinetest

import android.Manifest
import android.content.pm.PackageManager
import android.os.Bundle
import android.widget.Toast
import androidx.activity.result.contract.ActivityResultContracts
import androidx.appcompat.app.AppCompatActivity
import androidx.core.content.ContextCompat

class MainActivity : AppCompatActivity() {

    // Създаваме инстанция на твоя двигател
    private lateinit var audioCaptureManager: AudioCaptureManager

    // Модерен начин в Android за искане на права (Permissions)
    private val requestPermissionLauncher = registerForActivityResult(
        ActivityResultContracts.RequestPermission()
    ) { isGranted: Boolean ->
        if (isGranted) {
            // Потребителят е разрешил - пускаме записа!
            audioCaptureManager.startRecording()
            Toast.makeText(this, "Микрофонът е активен!", Toast.LENGTH_SHORT).show()
        } else {
            Toast.makeText(this, "Приложението се нуждае от микрофон, за да работи.", Toast.LENGTH_LONG).show()
        }
    }

    override fun onCreate(savedInstanceState: Bundle?) {
        super.onCreate(savedInstanceState)
        setContentView(R.layout.activity_main)

        audioCaptureManager = AudioCaptureManager()

        // Проверяваме правата веднага щом приложението стартира
        checkPermissionsAndStart()
    }

    private fun checkPermissionsAndStart() {
        if (ContextCompat.checkSelfPermission(this, Manifest.permission.RECORD_AUDIO)
            == PackageManager.PERMISSION_GRANTED) {
            // Вече имаме права от предишно пускане
            audioCaptureManager.startRecording()
        } else {
            // Нямаме права - показваме системния прозорец
            requestPermissionLauncher.launch(Manifest.permission.RECORD_AUDIO)
        }
    }

    override fun onDestroy() {
        super.onDestroy()
        // Спираме микрофона, когато приложението се затвори, за да не точи батерия
        audioCaptureManager.stopRecording()
    }
}