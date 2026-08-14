from django import forms
from django.conf import settings
from unfold.forms import BaseDialogForm
from unfold.widgets import (
    UnfoldAdminFileFieldWidget,
    UnfoldAdminIntegerFieldWidget,
)


class PromoCodeGenerationForm(BaseDialogForm):
    count = forms.IntegerField(
        label='Количество новых кодов',
        min_value=1,
        max_value=10_000_000,
        initial=1_500_000,
        help_text=(
            'Коды будут добавлены к уже существующим. Совпадения не входят '
            'в указанное количество.'
        ),
        widget=UnfoldAdminIntegerFieldWidget(
            attrs={
                'placeholder': 'Например, 1500000',
                'step': 1,
            }
        ),
    )


class PromoCodeImportForm(BaseDialogForm):
    file = forms.FileField(
        label='XLSX-файл',
        help_text=(
            'До 20 МБ. Промокоды читаются из первого столбца без заголовка; '
            'остальные столбцы игнорируются.'
        ),
        widget=UnfoldAdminFileFieldWidget(
            attrs={'accept': '.xlsx'},
        ),
    )

    def __init__(self, request, *args, **kwargs):
        if request.method == 'POST':
            kwargs['files'] = request.FILES
        super().__init__(request, *args, **kwargs)

    def clean_file(self):
        uploaded_file = self.cleaned_data['file']
        if not uploaded_file.name.lower().endswith('.xlsx'):
            raise forms.ValidationError('Загрузите файл в формате XLSX.')
        if uploaded_file.size > settings.XLSX_MAX_UPLOAD_SIZE:
            raise forms.ValidationError(
                'Размер файла не должен превышать 20 МБ.'
            )
        return uploaded_file
