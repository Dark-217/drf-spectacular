from textwrap import dedent

from django.core.management.base import BaseCommand
from django.utils.module_loading import import_string
from rest_framework import renderers

from drf_spectacular.app_settings import spectacular_settings
from drf_spectacular.renderers import NoAliasOpenAPIRenderer


class Command(BaseCommand):
    help = dedent("""
        Generate a spectacular OpenAPI3-compliant schema for your API.

        The warnings serve as a indicator for where your API could not be properly
        resolved. @extend_schema and @extend_schema_field are your friends.
        The spec should be valid in any case. If not, please open an issue
        on github: https://github.com/tfranzel/drf-spectacular/issues

        Remember to configure your APIs meta data like servers, version, url,
        documentation and so on in your SPECTACULAR_SETTINGS."
    """)

    def add_arguments(self, parser):
        parser.add_argument('--format', dest="format", choices=['openapi', 'openapi-json'], default='openapi', type=str)
        parser.add_argument('--urlconf', dest="urlconf", default=None, type=str)
        parser.add_argument('--generator-class', dest="generator_class", default=None, type=str)
        parser.add_argument('--file', dest="file", default=None, type=str)

    def handle(self, *args, **options):
        if options['generator_class']:
            generator_class = import_string(options['generator_class'])
        else:
            generator_class = spectacular_settings.DEFAULT_GENERATOR_CLASS

        generator = generator_class(urlconf=options['urlconf'])
        schema = generator.get_schema(request=None, public=True)
        renderer = self.get_renderer(options['format'])
        output = renderer.render(schema, renderer_context={})

        if options['file']:
            with open(options['file'], 'wb') as f:
                f.write(output)
        else:
            self.stdout.write(output.decode())

    def get_renderer(self, format):
        renderer_cls = {
            'openapi': NoAliasOpenAPIRenderer,
            'openapi-json': renderers.JSONOpenAPIRenderer,
        }[format]
        return renderer_cls()
