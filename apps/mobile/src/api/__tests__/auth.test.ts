import { MobileApiError } from '../client';
import { loginRequest, meRequest } from '../auth';

const fetchMock = jest.fn();

describe('mobile auth API', () => {
  beforeEach(() => {
    fetchMock.mockReset();
    global.fetch = fetchMock as unknown as typeof fetch;
  });

  it('posts credentials to /auth/login', async () => {
    fetchMock.mockResolvedValueOnce(
      new Response(
        JSON.stringify({
          access_token: 'access',
          refresh_token: 'refresh',
          token_type: 'bearer',
          athlete_id: 'athlete-1',
        }),
        { status: 200 }
      )
    );

    const result = await loginRequest('http://api.test', {
      email: 'athlete@example.com',
      password: 'secret',
    });

    expect(result.athlete_id).toBe('athlete-1');
    expect(fetchMock).toHaveBeenCalledWith(
      'http://api.test/auth/login',
      expect.objectContaining({
        method: 'POST',
        body: JSON.stringify({ email: 'athlete@example.com', password: 'secret' }),
      })
    );
  });

  it('sends bearer token to /auth/me', async () => {
    fetchMock.mockResolvedValueOnce(
      new Response(
        JSON.stringify({
          athlete_id: 'athlete-1',
          email: 'athlete@example.com',
          created_at: '2026-04-26T20:00:00Z',
          is_active: true,
        }),
        { status: 200 }
      )
    );

    await meRequest('http://api.test', 'access-token');

    const [, options] = fetchMock.mock.calls[0];
    expect(options.headers.Authorization).toBe('Bearer access-token');
  });

  it('surfaces backend detail on auth failure', async () => {
    fetchMock.mockResolvedValueOnce(
      new Response(JSON.stringify({ detail: 'Invalid credentials' }), { status: 401 })
    );

    await expect(
      loginRequest('http://api.test', {
        email: 'athlete@example.com',
        password: 'wrong',
      })
    ).rejects.toMatchObject<Partial<MobileApiError>>({
      status: 401,
      message: 'Invalid credentials',
    });
  });
});

