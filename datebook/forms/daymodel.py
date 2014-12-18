# -*- coding: utf-8 -*-
"""
Forms for day forms
"""
import datetime

from django import forms
from django.utils.translation import ugettext as _
from django.utils.timezone import now as tz_now, make_aware, utc

from datebook.models import DayEntry, DayModel
from datebook.forms.day import DATETIME_FORMATS, DayBaseFormMixin
from datebook.forms import CrispyFormMixin

class DayToDayModelForm(DayBaseFormMixin, CrispyFormMixin, forms.ModelForm):
    """
    DayModel form
    """
    crispy_form_helper_kwargs = {'day_to_model_mode': True}
    #crispy_form_helper_path = 'datebook.forms.crispies.day_helper'

    def __init__(self, author, *args, **kwargs):
        self.author = author
        self.dayentry = kwargs.pop('dayentry', None)
        self.daydate = kwargs.pop('day_date', None)
        
        # Args to give to the form layout method
        self.crispy_form_helper_kwargs.update({
            'form_action': kwargs.pop('form_action'),
        })
        
        # Fill initial datas
        kwargs = self.fill_initial_data(*args, **kwargs)
        
        super(DayToDayModelForm, self).__init__(*args, **kwargs)
        super(forms.ModelForm, self).__init__(*args, **kwargs)
        
        # Init some special fields
        kwargs = self.init_fields(*args, **kwargs)
    
    def save(self, *args, **kwargs):
        instance = super(DayToDayModelForm, self).save(commit=False, *args, **kwargs)
        instance.start = self.cleaned_data['start_datetime']
        instance.stop = self.cleaned_data['stop_datetime']
        instance.author = self.author
        instance.save()
        
        return instance
    
    class Meta:
        model = DayModel
        exclude = ('author', 'start', 'stop')
        widgets = {
            'pause': forms.TimeInput(format=DATETIME_FORMATS['input_time_formats'][0]),
            'overtime': forms.TimeInput(format=DATETIME_FORMATS['input_time_formats'][0]),
        }


class AssignDayModelForm(CrispyFormMixin, forms.Form):
    """
    Form to fill DayEntries with content from a DayModel
    """
    crispy_form_helper_path = 'datebook.forms.crispies.assign_daymodel_helper'
    
    def __init__(self, *args, **kwargs):
        self.author = kwargs.pop('author')
        self.datebook = kwargs.pop('datebook')
        self.daydate = self.datebook.period
        self.daychoices = [(item, str(item)) for item in kwargs.pop('daychoices')]
        self.daymodels_queryset = self.author.daymodel_set.all().order_by('title')
        
        super(AssignDayModelForm, self).__init__(*args, **kwargs)
        super(forms.Form, self).__init__(*args, **kwargs)
        
        # Init fields
        self.fields['days'] = forms.MultipleChoiceField(choices=self.daychoices, required=True)
        self.fields['daymodel'] = forms.ModelChoiceField(queryset=self.daymodels_queryset, required=True)

    def combine_day_and_daymodel_time(self, day_start, daymodel_start, daymodel_delta):
        """
        Combine the day date with the daymodel start time, then calcul the stop 
        from the start date and the given delta time (between daymodel start and 
        stop time)
        
        This way we have clean datetimes, correctly calculated with the right 
        day date and daymodel time.
        
        Return the calculated start and stop datetimes
        """
        if not isinstance(day_start, datetime.date):
            day_start = day_start.date()
            
        start = make_aware(datetime.datetime.combine(day_start, daymodel_start.time()), utc)
        return (
            start,
            start+daymodel_delta,
        )

    def save(self, *args, **kwargs):
        daymodel = self.cleaned_data['daymodel']
        daymodel_delta = daymodel.stop - daymodel.start
        # Bind datetime for each days using datebook period as the base date
        daydates = [self.daydate.replace(day=int(item)) for item in self.cleaned_data['days']]
        
        # Fill existing entries
        for entry in self.datebook.dayentry_set.filter(activity_date__in=daydates).order_by('activity_date'):
            # Get the start/stop datetimes
            goto_start, goto_stop = self.combine_day_and_daymodel_time(entry.start, daymodel.start, daymodel_delta)
            # Fill object attribute using the daymodel
            entry.start = goto_start
            entry.stop = goto_stop
            entry.pause = daymodel.pause
            entry.overtime = daymodel.overtime
            entry.content = daymodel.content
            entry.vacation = False # Allways remove the vacation
            entry.save()
            # Remove the day number from remaining selected days
            i = self.cleaned_data['days'].index(str(entry.activity_date.day))
            self.cleaned_data['days'].pop(i)
        
        # Create remaining selected days
        new_days = []
        for day_no in self.cleaned_data['days']:
            activity_date = self.datebook.period.replace(day=int(day_no))

            goto_start, goto_stop = self.combine_day_and_daymodel_time(activity_date, daymodel.start, daymodel_delta)
            
            new_days.append(DayEntry(
                datebook=self.datebook,
                activity_date=activity_date,
                start=goto_start,
                stop=goto_stop,
                pause=daymodel.pause,
                overtime=daymodel.overtime,
                content=daymodel.content,
                vacation=False,
            ))
        # Bulk create all new days
        if new_days:
            DayEntry.objects.bulk_create(new_days)
        # Update the datebook because model save method is not triggered with bulk creating
        self.datebook.modified = tz_now()
        self.datebook.save()
        
        return None
