from urllib.parse import urlparse, urlunparse, unquote, quote
import posixpath


class LinkCleaner:
    @staticmethod
    def clean(url):
        scheme, netloc, path, params, query, fragment = urlparse(url)
        if scheme not in ['http', 'https']:
            scheme, netloc, path, params, query, fragment = urlparse('https://' + url)

        if scheme not in ['http', 'https']:
            return None
        # Lower domain name
        netloc = netloc.lower()

        # Remove default port 80 or 443
        netloc_data = netloc.split(':')
        if len(netloc_data) > 2:
            return None

        if len(netloc_data) == 2:
            if scheme == 'http' and netloc_data[1] == '80':
                del netloc_data[1]
            elif scheme == 'https' and netloc_data[1] == '443':
                del netloc_data[1]

            netloc = ':'.join(netloc_data)

        # remove www
        if netloc.startswith('www.'):
            netloc = netloc[len('www.'):]
        # remove fragment and params
        fragment = ''
        params = False

        # fix path .. . and so on
        if len(path) > 0:
            path = posixpath.normpath(path)
        filename = None
        path_data = path.rsplit('/', 1)
        if len(path_data) == 1:
            path = '/'
        else:
            if len(path_data[0]) == 0 and len(path_data[1]) == 0:
                path = '/'
            else:
                if '.' in path_data[1]:
                    filename = path_data[1]
                    path = path_data[0]
        if len(path) == 0:
            path = '/'
        if not path.endswith('/'):
            path += '/'

        if filename is not None and filename in ['index.html', 'index.php']:
            filename = None

        # join
        if filename is not None:
            path = path + filename

        path = unquote(path)
        path = quote(path)
        new_url = urlunparse((scheme, netloc, path, params, query, fragment))
        return new_url
