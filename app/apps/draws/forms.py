from django import forms
from unfold.forms import BaseDialogForm
from unfold.widgets import UnfoldAdminDateWidget


class DrawReportForm(BaseDialogForm):
    date_from = forms.DateField(
        label='Дата начала',
        required=False,
        help_text='Оставьте пустым, чтобы выгрузить с начала акции.',
        widget=UnfoldAdminDateWidget,
    )
    date_to = forms.DateField(
        label='Дата окончания',
        required=False,
        help_text='Оставьте пустым, чтобы выгрузить по текущую дату.',
        widget=UnfoldAdminDateWidget,
    )

    def clean(self):
        cleaned_data = super().clean()
        date_from = cleaned_data.get('date_from')
        date_to = cleaned_data.get('date_to')
        if date_from and date_to and date_from > date_to:
            raise forms.ValidationError(
                'Дата начала не может быть позже даты окончания.'
            )
        return cleaned_data
