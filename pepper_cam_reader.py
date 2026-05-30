import cv2
import numpy as np
from naoqi import ALProxy

class NaoCamera:
    def __init__(self, ip, port, camera_index=0, resolution=1, color_space=13, frame_rate=30):
        self.ip = ip
        self.port = port
        self.camera_index = camera_index
        self.resolution = resolution
        self.color_space = color_space
        self.frame_rate = frame_rate
        self.camera_proxy = ALProxy("ALVideoDevice", ip, port)
        self.video_module = self.camera_proxy.subscribeCamera("python_client", self.camera_index,
                                                              self.resolution, self.color_space, self.frame_rate)

        # Initialize width and height attributes
        self.width = 0
        self.height = 0

    def get_frame(self):
        image_data = self.camera_proxy.getImageRemote(self.video_module)
        if image_data is None:
            return

        # Extract the image parameters
        self.width = image_data[0]
        self.height = image_data[1]

        # Convert the image data to a NumPy array
        image = np.frombuffer(image_data[6], dtype=np.uint8).reshape((self.height, self.width, 3))

        # Resize the frame using bilinear interpolation
        resized_image = cv2.resize(image, (self.width * 2, self.height * 2))

        return resized_image

    def release_camera(self):
        self.camera_proxy.unsubscribe(self.video_module)

    def camera_settings(self, brightness, contrast, saturation, hue, sharpness, exposure, gain):
        self.camera_proxy.setParam(0, brightness)  # kCameraBrightnessID
        self.camera_proxy.setParam(1, contrast)  # kCameraContrastID
        self.camera_proxy.setParam(2, saturation)  # kCameraSaturationID
        self.camera_proxy.setParam(3, hue)  # kCameraHueID
        self.camera_proxy.setParam(24, sharpness)  # kCameraSharpnessID
        self.camera_proxy.setParam(17, exposure)  # kCameraExposureID
        self.camera_proxy.setParam(6, gain)  # kCameraGainID

        self.camera_proxy.setParam(12, 1)  # Auto White Balance
        self.camera_proxy.setParam(11, 1)  # Auto Exposition
