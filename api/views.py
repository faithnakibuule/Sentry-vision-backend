import time, os
import threading
from django.http import StreamingHttpResponse, HttpResponse, JsonResponse
from django.views.decorators.csrf import csrf_exempt
from django.views.decorators.http import require_POST, require_GET
from .models import SecuritySnapshot

# Thread-safe global memory buffer for live streaming frames
LATEST_FRAME = None
FRAME_LOCK = threading.Lock()


# ------------------------------------------------------------------
# 1. LIVE STREAMING ENDPOINTS (ESP32 Live Feed -> In-Memory -> React)
# ------------------------------------------------------------------

@csrf_exempt
@require_POST
def upload_live(request):
    """
    ESP32 sends continuous frames (~20FPS) here.
    Updates the in-memory frame buffer in RAM.
    """
    global LATEST_FRAME
    
    if 'imageFile' in request.FILES:
        frame_bytes = request.FILES['imageFile'].read()
        with FRAME_LOCK:
            LATEST_FRAME = frame_bytes
        return HttpResponse("Frame received", status=200)
    
    return HttpResponse("Missing imageFile payload", status=400)


def generate_mjpeg_stream():
    """
    Generator yielding multipart MJPEG frames from the thread-safe buffer.
    """
    global LATEST_FRAME
    while True:
        with FRAME_LOCK:
            current_frame = LATEST_FRAME
            
        if current_frame is not None:
            yield (
                b'--frame\r\n'
                b'Content-Type: image/jpeg\r\n\r\n' + current_frame + b'\r\n'
            )
        
        # Throttles stream loop to ~25 FPS to conserve backend CPU
        time.sleep(0.04)


@require_GET
def live_stream_feed(request):
    """
    Streams the continuous MJPEG feed into the React <img> tag.
    """
    response = StreamingHttpResponse(
        generate_mjpeg_stream(),
        content_type='multipart/x-mixed-replace; boundary=frame'
    )
    # Prevent browser from aggressive caching or buffering
    response['Cache-Control'] = 'no-cache, no-store, must-revalidate'
    response['Pragma'] = 'no-cache'
    response['Expires'] = '0'
    return response

# ------------------------------------------------------------------
# 2. TRIGGERED SNAPSHOT ENDPOINTS (GPIO 12 Trigger -> DB / Disk)
# ------------------------------------------------------------------

@csrf_exempt
@require_POST
def upload_sd(request):
    """
    ESP32 posts high-priority snapshots here when triggered (GPIO 12 HIGH).
    Saves image to disk via Django ORM and logs metadata.
    """
    if 'imageFile' in request.FILES:
        image_file = request.FILES['imageFile']
        device_id = request.POST.get('device_id', 'ESP32_AI_CAM')
        
        snapshot = SecuritySnapshot.objects.create(
            device_id=device_id,
            image=image_file
        )
        
        return JsonResponse({
            "status": "success",
            "id": str(snapshot.id),
            "image_url": snapshot.image.url,
            "created_at": snapshot.created_at.isoformat()
        }, status=201)
        
    return JsonResponse({"error": "No imageFile provided"}, status=400)


@require_GET
def snapshot_list_api(request):
    """
    Returns a JSON list of recent trigger snapshots for the React gallery.
    """
    snapshots = SecuritySnapshot.objects.all()[:30] # Fetch latest 30 snapshots
    data = [
        {
            "id": str(s.id),
            "device_id": s.device_id,
            "image_url": request.build_absolute_uri(s.image.url),
            "created_at": s.created_at.strftime('%Y-%m-%d %H:%M:%S')
        }
        for s in snapshots
    ]
    return JsonResponse({"snapshots": data}, status=200)