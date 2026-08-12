from django import forms
from unfold.forms import BaseDialogForm
from unfold.widgets import UnfoldAdminIntegerFieldWidget


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
