# -*- coding: utf-8 -*-
"""
Forms
"""
from django import forms
from django.utils.translation import ugettext

from crispy_forms.helper import FormHelper
from crispy_forms_foundation.layout import Layout, Fieldset, SplitDateTimeField, RowFluid, Column, ButtonHolder, Submit

from datebook.models import Datebook

class DatebookForm(forms.ModelForm):
    """
    Datebook form
    """
    def __init__(self, author=None, *args, **kwargs):
        self.author = author
        
        self.helper = FormHelper()
        self.helper.form_action = '.'
        
        super(DatebookForm, self).__init__(*args, **kwargs)
    
    def save(self, *args, **kwargs):
        instance = super(DatebookForm, self).save(commit=False, *args, **kwargs)
        instance.author = self.author
        instance.save()
        
        return instance
    
    class Meta:
        model = Datebook