from django.test.runner import DiscoverRunner


class ProjectTestRunner(DiscoverRunner):
    default_test_labels = ('accounts', 'promo', 'draws', 'core')

    def run_tests(self, test_labels, **kwargs):
        return super().run_tests(
            test_labels or self.default_test_labels,
            **kwargs,
        )
