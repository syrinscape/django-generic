import cProfile
from io import StringIO
import pstats
import re
import sys

from django.conf import settings


class ConsoleExceptionMiddleware:
    """
    From http://www.djangosnippets.org/snippets/420/
    It shows the exception in the console. Useful if trying to debug an internal
    server error with Ajax queries. But crashes mod_wsgi since it uses print.
    """
    def process_exception(self, request, exception):
        if settings.DEBUG:
            import traceback
            exc_info = sys.exc_info()
            print("######################## Exception #############################")
            print('\n'.join(traceback.format_exception(*(exc_info or sys.exc_info()))))
            print("################################################################")
        return None

class ProfileMiddleware(object):
    """
    Adapted from http://djangosnippets.org/snippets/186/

    Displays profiling for any view.
    http://yoursite.com/yourview/?prof

    Add the "prof" key to query string by appending ?prof (or &prof=)
    and you'll see the profiling results in your browser.
    It's set up to only be available in django's debug mode, is available for superuser otherwise,
    but you really shouldn't add this middleware to any production configuration.

    WARNING: It uses hotshot profiler which is not thread safe.
    """
    words_re = re.compile( r'\s+' )
    group_prefix_re = [
        re.compile( "^.*/django/[^/]+" ),
        re.compile( "^(.*)/[^/]+$" ), # extract module path
        re.compile( ".*" ),           # catch strange entries
    ]

    def process_request(self, request):
        if (settings.DEBUG or request.user.is_superuser) and 'prof' in request.GET:
            self.prof = cProfile.Profile()

    def process_view(self, request, callback, callback_args, callback_kwargs):
        if (settings.DEBUG or request.user.is_superuser) and 'prof' in request.GET:
            return self.prof.runcall(callback, request, *callback_args, **callback_kwargs)

    def get_group(self, file):
        for g in ProfileMiddleware.group_prefix_re:
            name = g.findall( file )
            if name:
                return name[0]

    def get_summary(self, results_dict, sum):
        list = [ (item[1], item[0]) for item in results_dict.items() ]
        list.sort( reverse = True )
        list = list[:40]

        res = "      tottime\n"
        for item in list:
            res += "%4.1f%% %7.3f %s\n" % ( 100*item[0]/sum if sum else 0, item[0], item[1] )

        return res

    def summary_for_files(self, stats_str):
        stats_str = stats_str.split("\n")[5:]

        mystats = {}
        mygroups = {}

        sum = 0

        for s in stats_str:
            fields = ProfileMiddleware.words_re.split(s);
            if len(fields) == 7:
                time = float(fields[2])
                sum += time
                file = fields[6].split(":")[0]

                if not file in mystats:
                    mystats[file] = 0
                mystats[file] += time

                group = self.get_group(file)
                if not group in mygroups:
                    mygroups[ group ] = 0
                mygroups[ group ] += time

        return "<pre>" + \
               " ---- By file ----\n\n" + self.get_summary(mystats,sum) + "\n" + \
               " ---- By group ---\n\n" + self.get_summary(mygroups,sum) + \
               "</pre>"

    def process_response(self, request, response):
        if (settings.DEBUG or request.user.is_superuser) and 'prof' in request.GET:
            out = StringIO()
            stats = pstats.Stats(self.prof, stream=out)
            stats.sort_stats('time', 'calls')
            stats.print_stats()
            stats_str = out.getvalue()

            if response.content and stats_str:
                content = "<pre>" + stats_str + "</pre>"
            else:
                content = response.content.decode(response.charset)
            content = "\n".join(content.split("\n")[:40])
            content += self.summary_for_files(stats_str)
            response.content = content

        return response
