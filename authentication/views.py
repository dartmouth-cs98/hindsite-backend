from rest_framework import (
    permissions, viewsets, views, status, authentication
)
from authentication.models import CustomUser
from authentication.permissions import IsCustomUserOwner
from authentication.serializers import (
                CustomUserSerializer, TokenSerializer,
                LoginSerializer, UserInfoSerializer, KeysSerializer,
                )
from rest_framework.response import Response
from django.contrib.auth import authenticate, login, logout
from rest_framework.authtoken.models import Token
from django.utils import timezone
from datetime import datetime, timedelta
import json
from history.models import Category, Domain, PageVisit
from history.common import is_blacklisted
from history.tasks import create_page
import base64, hashlib
from urllib.parse import urlparse
from authentication.tasks import (
    complete_signup, forgot_password, change_password, close_all
)
from hindsite.constants import weekdays

class CreateCustomUserView(views.APIView):
    lookup_field = 'username'
    queryset = CustomUser.objects.all()
    serializer_class = CustomUserSerializer
    permission_classes = ()

    def post(self, request, format=None):

        request.data['email'] = request.data['email'].lower()

        request.data['username'] = request.data['email']

        if 'offset' not in request.data.keys():
            request.data['offset'] = 0

        if CustomUser.objects.filter(email=request.data['email']).exists():
            return Response({
                'status': 'Account Exists',
                'message': 'An account with this email already exists.'
            }, status=status.HTTP_400_BAD_REQUEST)

        serializer = self.serializer_class(data=request.data)

        if serializer.is_valid():
            customuser = CustomUser.objects.create_user(**serializer.validated_data)

            complete_signup.delay(customuser.pk)

            token = Token.objects.get(user=customuser)

            key = base64.b64encode(customuser.key.encode()).decode()
            md5 = base64.b64encode(hashlib.md5(customuser.key.encode()).digest()).decode()
            data = {'token': token.key,
                    'key': key,
                    'md5': md5,
                    'categories': customuser.category_set.all(),
                    'tracking': customuser.tracking_on}

            send = LoginSerializer(data)

            return Response(send.data)

        return Response({
            'status': 'Bad request',
            'message': 'Account could not be created with received data.'
        }, status=status.HTTP_400_BAD_REQUEST)

class LoginView(views.APIView):
    authentication_classes = ()
    permission_classes = ()

    def post(self, request, format=None):

        email = request.data['email'].lower()
        password = request.data['password']

        customuser = authenticate(email=email, password=password)

        if customuser is not None:
            if customuser.is_active:
                login(request, customuser)

                if 'offset' in request.data.keys():
                    customuser.offset = request.data['offset']
                    customuser.save()
                
                token = Token.objects.get(user=customuser)
                key = base64.b64encode(customuser.key.encode()).decode()
                md5 = base64.b64encode(hashlib.md5(customuser.key.encode()).digest()).decode()
                data = {'token': token.key,
                        'key': key,
                        'md5': md5,
                        'categories': customuser.category_set.all(),
                        'tracking': customuser.tracking_on}

                send = LoginSerializer(data)

                return Response(send.data)
            else:
                return Response({
                    'status': 'Unauthorized',
                    'message': 'This account has been disabled.'
                }, status=status.HTTP_401_UNAUTHORIZED)
        else:
            return Response({
                'status': 'Unauthorized',
                'message': 'Username/password combination invalid.'
            }, status=status.HTTP_401_UNAUTHORIZED)

class LogoutView(views.APIView):

    def post(self, request, format=None):

        cu = request.user

        close_all.delay(cu.pk)

        logout(request)

        return Response({}, status=status.HTTP_204_NO_CONTENT)

class ForgotPassword(views.APIView):
    permission_classes = ()

    def post(self, request, format=None):

        email_send = request.data['email'].lower()

        customuser = CustomUser.objects.filter(email=email_send)

        if customuser.exists():
            customuser = customuser.first()

            forgot_password.delay(customuser.pk)

        return Response()

class ChangePassword(views.APIView):
    permission_classes = (permissions.IsAuthenticated,)

    def post(self, request, format=None):

        current_pw = request.data['current_pw']
        new_pw = request.data['new_pw']

        customuser = authenticate(email=request.user.email, password=current_pw)

        if customuser is not None:

            change_password.delay(customuser.pk, new_pw)

            return Response({
                'status': 'OK',
                'message': 'Password successfully updated'
                })
        else:
            return Response({
                'status': 'Unauthorized',
                'message': 'Current password incorrect'
            }, status=status.HTTP_401_UNAUTHORIZED)

class ChangeTracking(views.APIView):
    permission_classes = (permissions.IsAuthenticated,)

    def post(self, request, format=None):
        cu = request.user

        tracking = request.data['tracking']

        cu.tracking_on = tracking
        cu.save()

        if not tracking:
            close_all.delay(cu.pk)
        else:
            url = request.data['url']
            base_url = urlparse(url).netloc

            if not is_blacklisted(cu, base_url):
                t_id = request.data['tab']
                page_title = request.data['title']
                domain_title = request.data['domain']

                if 'favIconUrl' in request.data.keys():
                    favicon = request.data['favIconUrl']
                else:
                    favicon = ''

                if 'html' in request.data.keys():
                    html = request.data['html']
                else:
                    html = ''

                if 'image' in request.data.keys():
                    image = request.data['image'].split(',')[1]
                else:
                    image = ''

                if 'previousTabId' in request.data.keys():
                    prev_tab = request.data['previousTabId']
                else:
                    prev_tab = t_id
                active = request.data['active']

                create_page.delay(cu.pk, url, base_url, t_id,
                                 page_title, domain_title, favicon, html,
                                 image, prev_tab, active)

        user = UserInfoSerializer(cu)

        return Response(user.data)

class GetDecryption(views.APIView):

    def get(self, request, format=None):
        cu = request.user

        token = Token.objects.get(user=cu)
        key = base64.b64encode(cu.key.encode()).decode()
        md5 = base64.b64encode(hashlib.md5(cu.key.encode()).digest()).decode()
        data = {'token': token.key,
                'key': key,
                'md5': md5}

        send = KeysSerializer(data)

        return Response(send.data)
