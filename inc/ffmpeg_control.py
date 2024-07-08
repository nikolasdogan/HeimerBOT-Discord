import subprocess

def ffmpeg_if():
    try:
        # FFmpeg'in sürümünü kontrol etmek için komutu çalıştırın
        result = subprocess.run(['ffmpeg', '-version'], capture_output=True, text=True)
        print(result.stdout)
        return True
    except FileNotFoundError:
        print("FFmpeg bulunamadı. Lütfen FFmpeg'in doğru yüklendiğinden emin olun.")
        return False