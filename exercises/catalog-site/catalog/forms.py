"""Forms for public catalog writes."""

from django import forms

from .models import Review, Submission


# [Implementation 8]
# Public forms expose only user-editable fields; author, entry, and moderation values come from the server.
class ReviewForm(forms.ModelForm):
    class Meta:
        model = Review
        fields = ("rating", "body")
        widgets = {
            "rating": forms.NumberInput(attrs={"min": 1, "max": 5}),
            "body": forms.Textarea(attrs={"rows": 6}),
        }

    def clean_body(self) -> str:
        body = self.cleaned_data["body"].strip()
        if len(body) < 10:
            raise forms.ValidationError("후기는 10자 이상 작성해 주세요.")
        return body


class SubmissionForm(forms.ModelForm):
    class Meta:
        model = Submission
        fields = ("title", "summary", "source_url")

    def clean_title(self) -> str:
        title = self.cleaned_data["title"].strip()
        if len(title) < 2:
            raise forms.ValidationError("제목은 2자 이상 작성해 주세요.")
        return title

    def clean_summary(self) -> str:
        summary = self.cleaned_data["summary"].strip()
        if len(summary) < 10:
            raise forms.ValidationError("요약은 10자 이상 작성해 주세요.")
        return summary
