/* eslint-disable */
import { sleep } from 'k6';
import http from 'k6/http';

export const options = {
  duration: '10m',
  vus: 100,
  //  vus: 1,
  thresholds: {
    //avg is around ?500ms? on https://jassari.api.stage.hel.ninja
    http_req_duration: ['p(95)<5000'],
  },
};

export default () => {
  let url = 'https://jassari.api.stage.hel.ninja/graphql';
  if (`${__ENV.K6_LOADTEST_ENV_URL}` != 'undefined') {
    url = `${__ENV.K6_LOADTEST_ENV_URL}`;
  }
  const data = 'query=query Organisations {organisations {edges {node {id } } } }';
  const res = http.post(url, data, {
    headers: { 'Content-Type': 'application/x-www-form-urlencoded' },
  });

  //10 loads per minute
  sleep(6);
};
