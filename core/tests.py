from django.test import TestCase
from django.core.files.uploadedfile import SimpleUploadedFile
from django.contrib.auth import get_user_model
from rest_framework.test import APIClient
from rest_framework import status

User = get_user_model()

class ProfilePictureUploadTests(TestCase):
    def setUp(self):
        self.client = APIClient()
        self.user = User.objects.create_user(
            username='testuser',
            email='testuser@futb.edu.ng',
            password='testpassword123',
            first_name='Test',
            last_name='User',
            department='Computer Science',
            faculty='Science',
        )
        self.client.force_authenticate(user=self.user)

    def test_upload_profile_picture_jpeg(self):
        # 1x1 transparent/black GIF or JPEG bytes
        image_content = (
            b'\xff\xd8\xff\xe0\x00\x10JFIF\x00\x01\x01\x01\x00`\x00`\x00\x00'
            b'\xff\xdb\x00C\x00\x08\x06\x06\x07\x06\x05\x08\x07\x07\x07\t\t'
            b'\x08\n\x0c\x14\r\x0c\x0b\x0b\x0c\x19\x12\x13\x0f\x14\x1d\x1a'
            b'\x1f\x1e\x1d\x1a\x1c\x1c $.\' ",#\x1c\x1c(7),01444\x1f\'9=82<.342'
            b'\xff\xc0\x00\x0b\x08\x00\x01\x00\x01\x01\x01\x11\x00'
            b'\xff\xc4\x00\x1f\x00\x00\x01\x05\x01\x01\x01\x01\x01\x01\x00\x00'
            b'\x00\x00\x00\x00\x00\x00\x01\x02\x03\x04\x05\x06\x07\x08\t\n\x0b'
            b'\xff\xda\x00\x08\x01\x01\x00\x00?\x00\xbf\x00\xff\xd9'
        )
        image = SimpleUploadedFile('avatar.jpg', image_content, content_type='image/jpeg')
        response = self.client.patch('/api/auth/profile/picture/', {'profile_picture': image}, format='multipart')
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.assertIn('profile_picture_url', response.data)
        self.assertIsNotNone(response.data['profile_picture_url'])
        self.assertTrue('profile_pictures/' in response.data['profile_picture_url'])
        self.user.refresh_from_db()
        self.assertTrue(bool(self.user.profile_picture))

    def test_upload_no_file(self):
        response = self.client.patch('/api/auth/profile/picture/', {}, format='multipart')
        self.assertEqual(response.status_code, status.HTTP_400_BAD_REQUEST)
        self.assertEqual(response.data.get('error'), 'No image file provided')

    def test_upload_invalid_file_type(self):
        txt_file = SimpleUploadedFile('notes.txt', b'Hello world', content_type='text/plain')
        response = self.client.patch('/api/auth/profile/picture/', {'profile_picture': txt_file}, format='multipart')
        self.assertEqual(response.status_code, status.HTTP_400_BAD_REQUEST)
        self.assertEqual(response.data.get('error'), 'Only JPEG, PNG and WebP images are allowed')
