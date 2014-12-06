# -*- coding: utf-8 -*-
"""
Datebook month views
"""
import datetime

from django import http
from django.views import generic
from django.contrib.auth.models import User

from braces.views import LoginRequiredMixin, PermissionRequiredMixin

from datebook.forms.month import DatebookForm
from datebook.models import Datebook
from datebook.mixins import DatebookCalendarMixin, DatebookCalendarAutoCreateMixin, OwnerOrPermissionRequiredMixin
from datebook.utils import format_seconds_to_clock

class DatebookMonthFormView(PermissionRequiredMixin, generic.FormView):
    """
    Datebook create form view
    """
    model = Datebook
    form_class = DatebookForm
    template_name = 'datebook/month/form.html'
    permission_required = 'datebook.add_datebook'
    raise_exception = True

    def get_form(self, form_class):
        excluded_users = Datebook.objects.all().values('author_id').distinct()
        self.available_users = User.objects.all().exclude(pk__in=[v['author_id'] for v in excluded_users]).order_by('username')
        
        if self.available_users.count() == 0:
            return None
        return super(DatebookMonthFormView, self).get_form(form_class)
        
    def get_form_kwargs(self, **kwargs):
        kwargs = super(DatebookMonthFormView, self).get_form_kwargs(**kwargs)
        kwargs.update({
            'available_users': self.available_users,
        })
        return kwargs
    
    def form_valid(self, form):
        self.object = form.save()
        return super(DatebookMonthFormView, self).form_valid(form)
    
    def get_success_url(self):
        return self.object.get_absolute_url()


class DatebookMonthGetOrCreateView(DatebookCalendarMixin, OwnerOrPermissionRequiredMixin, generic.View):
    """
    Automatically create the datebook if it does not allready exists for the "author+year+month" 
    kwargs given, then redirect to its page.
    
    If the Datebook allready exists for the given kwargs, raise a "Http404"
    """
    permission_required = 'datebook.add_datebook'
    raise_exception = True
    
    def get(self, request, *args, **kwargs):
        if Datebook.objects.filter(author=self.author, period__year=self.year, period__month=self.month).count()>0:
            raise http.Http404
        
        d = self.author.datebook_set.create(period=datetime.date(year=self.year, month=self.month, day=1))
        
        return http.HttpResponseRedirect(d.get_absolute_url())


class DatebookMonthCurrentView(DatebookCalendarAutoCreateMixin, OwnerOrPermissionRequiredMixin, generic.View):
    """
    Automatically create the datebook if it does not allready exists for the "author" 
    kwarg and the current month, then redirect to its page.
    
    If the Datebook allready exists for the given kwargs, directly redirect to it
    """
    def get(self, request, *args, **kwargs):
        self.get_current_date()
        
        q = Datebook.objects.filter(author=self.author, period__year=self.year, period__month=self.month)
        
        if q.count()>0:
            d = q.order_by('period')[0:1][0]
        else:
            d = self.author.datebook_set.create(period=datetime.date(year=self.year, month=self.month, day=1))
        
        return http.HttpResponseRedirect(d.get_absolute_url())


class DatebookMonthView(LoginRequiredMixin, DatebookCalendarMixin, generic.TemplateView):
    """
    Datebook month details view
    
    Get the Calendar for the given year+month then fill it with day entries
    """
    template_name = "datebook/month/calendar.html"
    
    def get_calendar(self, day_filters={}):
        # Add current day if the datebook period is the current month+year
        #current_day = None
        current_day = datetime.date.today()
        #print _curr.replace(day=1), self.object.period
        #if _curr.replace(day=1) == self.object.period:
            #current_day = _curr
        
        _cal = super(DatebookMonthView, self).get_calendar()
        
        # Calculate total elapsed time for worked days
        day_entries = self.get_dayentry_list(day_filters)
        total_elapsed_time = total_overtime_seconds = total_vacation = 0
        for item in day_entries:
            if item.vacation:
                total_vacation += 1
                continue
            total_elapsed_time += item.get_elapsed_seconds()
            total_overtime_seconds += item.get_overtime_seconds()
        
        return {
            "weekheader": _cal.formatweekheader(),
            "month": _cal.formatmonth(self.object.period.year, self.object.period.month, dayentries=day_entries, current_day=current_day),
            "total_elapsed_time": format_seconds_to_clock(total_elapsed_time),
            "total_overtime_seconds": total_overtime_seconds,
            "total_overtime_time": format_seconds_to_clock(total_overtime_seconds),
            "total_vacation": total_vacation,
        }
        
    def get_context_data(self, **kwargs):
        context = super(DatebookMonthView, self).get_context_data(**kwargs)
        context.update({
            'datebook': self.object,
            'datebook_calendar': self.get_calendar(),
        })
        return context
    
    def get(self, request, *args, **kwargs):
        self.object = self.get_datebook({'period__year': self.year, 'period__month': self.month})
        
        context = self.get_context_data(**kwargs)
        
        return self.render_to_response(context)
