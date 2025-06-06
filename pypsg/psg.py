import os
import requests
from pkg_resources import resource_string
from io import StringIO
from collections import OrderedDict
import re
import time
import numpy as np


class PSG():
    def __init__(self, server_url='https://psg.gsfc.nasa.gov/api.php', 
                       timeout_seconds=10, api_key=None, 
                       default_config='resources/default.config'):
        self._server_url = server_url
        self._timeout_seconds = timeout_seconds
        self._api_key = api_key
        if os.path.isabs(default_config):
            with open(default_config, "r") as foo:
                self.default_config_str = foo.read()
        else:
            self.default_config_str = resource_string(__name__, default_config).decode('utf-8')
        self.default_config = self.config_str_to_dict(self.default_config_str)

        print('Testing connection to PSG at {} ...'.format(self._server_url))
        self.run(self.default_config)
        print('Connected to PSG with success.')

    @staticmethod
    def config_str_to_dict(config_str):
        psg_regex = r"<(.+?)>(.*)"
        matches = re.finditer(psg_regex, config_str, re.MULTILINE)

        ret = OrderedDict()
        for match in matches:
            key = match.group(1)
            value = match.group(2)
            try:
                value = int(value)
            except ValueError:
                try:
                    value = float(value)
                except ValueError:
                    value = value
            ret[key] = value
        return ret

    @staticmethod
    def config_dict_to_str(config_dict):
        ret = []
        for key, value in config_dict.items():
            ret.append('<{}>{}'.format(key, str(value)))
        return '\n'.join(ret)

    def run(self, config=None, config_str=None, watm=None, otype=None):
        if config_str is None:
            if config is None:
                raise ValueError('Expecting either config or config_str.')
            else:
                config_str = self.config_dict_to_str(config)

        time_start = time.time()
        data = {'file': config_str}
        if self._api_key is not None:
            data['key'] = self._api_key
        if watm is not None:
            data['watm'] = watm
        if otype is not None:
            data['type'] = otype
        reply = requests.post(self._server_url, data=data, timeout=self._timeout_seconds)
        time_duration = time.time() - time_start
        if reply.status_code == requests.codes.ok:
            reply_raw = reply.text
        else:
            raise RuntimeError('Unexpected HTTP status code received from PSG: {}'.format(reply.status_code))

        reply_header = []
        reply_data = []
        for line in reply_raw.splitlines():
            if line.startswith('#'):
                reply_header.append(line)
            else:
                reply_data.append(line)

        reply_header_str = '\n'.join(reply_header)
        try:
            reply_data_np = np.loadtxt(StringIO('\n'.join(reply_data)))
            return {'header': reply_header_str, 'spectrum': reply_data_np, 'duration_seconds': time_duration}
        except:
            if otype == 'cfg':
                return {'config': reply_raw}
            elif otype == 'ret':
                reply_raw = reply_raw.replace('<br/>', '\n').replace('&nbsp;', '')
                pattern = re.compile(r"results_(.+)\.txt")
                iterator = pattern.finditer(reply_raw)
                spans = [match.span() for match in iterator]
                names = [reply_raw[spans[i][0] : spans[i][1]].replace('results_', '').replace('.txt', '')
                         for i in range(len(spans))]
                ret = {}
                for i in range(len(spans)):
                    if i < len(spans)-1:
                        ret[names[i]] = reply_raw[spans[i][1] : spans[i+1][0]].strip()
                    else:
                        ret[names[i]] = reply_raw[spans[i][1]:].strip()
                return ret
            else:
                return {'reply' : reply_raw}


