from django import forms
from unfold.forms import BaseDialogForm


DATE_INPUT_CLASSES = ' '.join(
    (
        'border',
        'border-base-200',
        'bg-white',
        'font-medium',
        'min-w-20',
        'rounded-default',
        'shadow-xs',
        'text-font-default-light',
        'text-sm',
        'focus:outline-2',
        'focus:-outline-offset-2',
        'focus:outline-primary-600',
        'group-[.errors]:border-red-600',
        'dark:bg-base-900',
        'dark:border-base-700',
        'dark:text-font-default-dark',
        'dark:scheme-dark',
        'px-3',
        'py-2',
        'w-full',
    )
)


class AdminDateInput(forms.DateInput):
    input_type = 'date'

    def __init__(self):
        super().__init__(
            format='%Y-%m-%d',
            attrs={'class': DATE_INPUT_CLASSES},
        )


class DrawReportForm(BaseDialogForm):
    date_from = forms.DateField(
        label='Дата начала',
        required=False,
        help_text='Оставьте пустым, чтобы выгрузить с начала акции.',
        widget=AdminDateInput,
    )
    date_to = forms.DateField(
        label='Дата окончания',
        required=False,
        help_text='Оставьте пустым, чтобы выгрузить по текущую дату.',
        widget=AdminDateInput,
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
