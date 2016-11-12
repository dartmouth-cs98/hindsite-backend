from history.models import Tab, Domain, Page, PageVisit, TimeActive, Category
from django.http import Http404, HttpResponse
from rest_framework.views import APIView
from rest_framework.response import Response
from rest_framework import status
from django.utils import timezone
from django.db.models import Q
from datetime import datetime, timedelta
import pytz
from django.core import serializers
from history.serializers import SendTabSerializer, SendCategorySerializer

class SendTabs(APIView):
    """
    Send info for lookback page
    """
    def post(self, request, format=None):
        start = request.data['start']
        end = request.data['end']

        start = pytz.utc.localize(datetime.strptime(start, '%Y-%m-%dT%H:%M:%S.%fZ'))
        end = pytz.utc.localize(datetime.strptime(end, '%Y-%m-%dT%H:%M:%S.%fZ'))

        #domains open during timeframe
        domains = Domain.objects.filter(Q(created__range=[start, end]) |
                              Q(closed__range=[start, end]) |
                              (Q(closed__gte=end) & Q(created__lte=start)) |
                              (Q(created__lte=start) & Q(closed__isnull=True))
                              )

        # pvs = PageVisit.objects.filter(visited__range=[start, end])

        tabs = set()

        for d in domains:
            tabs.add(d.tab)

        domains = list(domains)
        holder = {'tabs': []}

        for t in tabs:
            setattr(t, 'domains', [])

            for d in domains:
                if d.tab == t and d not in t.domains:

                    c = pvs.filter(domain=d).count()

                    # handle case where start and end time are before and
                    # after that day but go through the whole day
                    ta = d.active_times.filter(Q(start__range=[start, end]) |
                                               Q(end__range=[start, end]))

                    minutes_active = 0

                    for a in ta:
                        if a.start < start:
                            time = a.end - start
                        elif a.end is None or a.end > end:
                            time = end - a.start
                        else:
                            time = a.end - a.start
                        minutes_active += int(time.seconds / 60)

                    setattr(d, 'pages', c)
                    setattr(d, 'active_times', ta)
                    setattr(d, 'minutes_active', minutes_active)

                    t.domains.append(d)
            holder['tabs'].append(t)

        send = SendTabSerializer(holder)


        return Response(send.data)

class SendCategories(APIView):
    """
    Send categories with their associated pages
    """
    def get(self, request, format=None):
        holder = {'categories': []}

        starred = Page.objects.filter(star=True)

        holder['starred'] = starred

        cats = Category.objects.all()

        for c in cats:
            pages = c.page_set.all()

            setattr(c, 'pages', pages)

            holder['categories'].append(c)

        send = SendCategorySerializer(holder)

        return Response(send.data)
