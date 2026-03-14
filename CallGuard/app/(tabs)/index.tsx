import { useState, useRef } from 'react';
import { View, Text, TouchableOpacity, StyleSheet, Platform } from 'react-native';
import { useAudioRecorder, AudioModule, RecordingPresets } from 'expo-audio';
import * as DocumentPicker from 'expo-document-picker';

const BACKEND_URL = Platform.select({
    web: 'http://127.0.0.1:8000/predict',
    default: 'http://172.20.10.11:8000/predict',
}) as string;

export default function HomeScreen() {
    const [isProtected, setIsProtected] = useState(false);
    const [status, setStatus] = useState('Ready to Scan');
    const audioRecorder = useAudioRecorder(RecordingPresets.HIGH_QUALITY);
    const intervalRef = useRef<any>(null);

    async function startProtection() {
        await AudioModule.requestRecordingPermissionsAsync();
        await audioRecorder.prepareToRecordAsync();
        await AudioModule.setAudioModeAsync({ allowsRecording: true, playsInSilentMode: true });
        audioRecorder.record();
        setIsProtected(true);
        setStatus('Shield Active - Scanning...');

        intervalRef.current = setInterval(async () => {
            await audioRecorder.stop();
            const uri = audioRecorder.uri;
            if (uri) await sendAudio(uri, 'audio.m4a', 'audio/m4a');
            await audioRecorder.prepareToRecordAsync();
            audioRecorder.record();
        }, 3000);
    }

    async function sendAudio(
        uri: string | null,
        fileName: string,
        fileType: string,
        webFile?: File,
    ) {
        const formData = new FormData();
        if (webFile) {
            formData.append('file', webFile, fileName);
        } else if (uri) {
            formData.append('file', { uri, name: fileName, type: fileType } as any);
        } else {
            setStatus('Missing file data');
            return;
        }

        try {
            const response = await fetch(BACKEND_URL, { method: 'POST', body: formData });
            const result = await response.json().catch(() => ({}));

            if (!response.ok) {
                setStatus(`Backend error: ${result?.detail || response.status}`);
                return;
            }

            console.log('Отговор:', JSON.stringify(result));
            const accuracyPercent = typeof result.accuracy === 'number'
                ? ` (${Math.round(result.accuracy * 100)}%)`
                : '';
            setStatus(`${result.status || 'scanning'}${accuracyPercent}`);
        } catch (e) {
            console.log('Грешка:', e);
            setStatus('Network error');
        }
    }

    async function uploadWavFile() {
        try {
            const result = await DocumentPicker.getDocumentAsync({
                type: ['audio/wav', 'audio/x-wav'],
                copyToCacheDirectory: true,
            });

            if (result.canceled) {
                return;
            }

            const picked = result.assets?.[0];
            if (!picked?.uri) {
                setStatus('No file selected');
                return;
            }

            const name = picked.name || 'upload.wav';
            const isWav = name.toLowerCase().endsWith('.wav');
            if (!isWav) {
                setStatus('Please choose a .wav file');
                return;
            }

            setStatus('Uploading WAV...');
            const webFile = (picked as any).file as File | undefined;
            if (Platform.OS === 'web' && webFile) {
                await sendAudio(null, name, picked.mimeType || 'audio/wav', webFile);
            } else {
                await sendAudio(picked.uri, name, picked.mimeType || 'audio/wav');
            }
        } catch (e) {
            console.log('File picker error:', e);
            setStatus('Could not pick file');
        }
    }

    async function stopProtection() {
        clearInterval(intervalRef.current);
        await audioRecorder.stop();
        setIsProtected(false);
        setStatus('Ready to Scan');
    }

    return (
        <View style={styles.container}>
            <Text style={styles.title}>AI Call Guard</Text>
            <Text style={styles.status}>{status}</Text>
            <TouchableOpacity
                style={[styles.button, isProtected ? styles.stop : styles.start]}
                onPress={isProtected ? stopProtection : startProtection}
            >
                <Text style={styles.buttonText}>
                    {isProtected ? 'STOP PROTECTION' : 'START PROTECTION'}
                </Text>
            </TouchableOpacity>

            <TouchableOpacity
                style={[styles.button, styles.upload]}
                onPress={uploadWavFile}
            >
                <Text style={styles.buttonText}>UPLOAD WAV FILE</Text>
            </TouchableOpacity>
        </View>
    );
}

const styles = StyleSheet.create({
    container: { flex: 1, justifyContent: 'center', alignItems: 'center', backgroundColor: '#fff' },
    title: { fontSize: 24, fontWeight: 'bold', marginBottom: 20 },
    status: { fontSize: 18, marginBottom: 30, color: '#555' },
    button: { padding: 20, borderRadius: 10, width: 250, alignItems: 'center' },
    start: { backgroundColor: 'green' },
    stop: { backgroundColor: 'red' },
    upload: { backgroundColor: '#2563eb', marginTop: 12 },
    buttonText: { color: 'white', fontSize: 16, fontWeight: 'bold' },
});
