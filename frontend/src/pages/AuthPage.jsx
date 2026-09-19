import React, { useState } from 'react';
import { useNavigate } from 'react-router-dom';
import video1 from '../../../assets/video1.mp4';

export default function AuthPage() {
  const navigate = useNavigate();
  const [authState, setAuthState] = useState('login'); // 'login', 'register1', 'register2'
  const [email, setEmail] = useState('');
  const [password, setPassword] = useState('');
  const [confirmPassword, setConfirmPassword] = useState('');
  const [username, setUsername] = useState('');
  const [showPassword, setShowPassword] = useState(false);
  const [showRegPassword, setShowRegPassword] = useState(false);
  const [showConfirmPassword, setShowConfirmPassword] = useState(false);
  const [loading, setLoading] = useState(false);
  const [errorMsg, setErrorMsg] = useState('');

  const handleLoginSubmit = async (e) => {
    e.preventDefault();
    setLoading(true);
    setErrorMsg('');
    try {
      const response = await fetch('/api/v1/auth/login', {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({ email, password })
      });
      
      const data = await response.json();
      if (!response.ok) {
        let errorMsg = 'Login failed. Please check your credentials.';
        if (data.detail) {
          if (Array.isArray(data.detail)) {
            errorMsg = data.detail.map(err => err.msg).join(', ');
          } else {
            errorMsg = typeof data.detail === 'string' ? data.detail : JSON.stringify(data.detail);
          }
        }
        throw new Error(errorMsg);
      }
      
      localStorage.setItem('satquery_access_token', data.access_token);
      if (data.refresh_token) {
        localStorage.setItem('satquery_refresh_token', data.refresh_token);
      }
      navigate('/dashboard');
    } catch (err) {
      setErrorMsg(err.message);
    } finally {
      setLoading(false);
    }
  };

  const handleRegisterStep1 = (e) => {
    e.preventDefault();
    if (!email) return;
    setErrorMsg('');
    setAuthState('register2');
  };

  const handleRegisterStep2 = async (e) => {
    e.preventDefault();
    if (password !== confirmPassword) {
      setErrorMsg('Passwords do not match. Please verify.');
      return;
    }
    setLoading(true);
    setErrorMsg('');
    try {
      const response = await fetch('/api/v1/auth/register', {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({ 
          email, 
          password, 
          display_name: username 
        })
      });
      
      const data = await response.json();
      if (!response.ok) {
        let errorMsg = 'Registration failed. Try a different email.';
        if (data.detail) {
          if (Array.isArray(data.detail)) {
            // FastAPI 422 validation error
            errorMsg = data.detail.map(err => err.msg).join(', ');
          } else {
            errorMsg = typeof data.detail === 'string' ? data.detail : JSON.stringify(data.detail);
          }
        }
        throw new Error(errorMsg);
      }
      
      localStorage.setItem('satquery_access_token', data.access_token);
      if (data.refresh_token) {
        localStorage.setItem('satquery_refresh_token', data.refresh_token);
      }
      navigate('/dashboard');
    } catch (err) {
      setErrorMsg(err.message);
    } finally {
      setLoading(false);
    }
  };

  return (
    <div className="bg-white font-sans text-slate-900 antialiased h-screen w-screen overflow-hidden select-none">
      <main className="w-screen h-screen min-h-screen overflow-hidden flex flex-row">
        
        {/* LEFT 50%: Persistent Cinematic Hero & Satellite Display */}
        <section className="w-1/2 h-full relative overflow-hidden bg-black flex flex-col justify-between p-10 lg:p-14 shrink-0">
          {/* Full Bleed Video Hero with Poster Fallback */}
          <video 
            autoPlay 
            className="absolute inset-0 w-full h-full object-cover" 
            id="satquery-video" 
            muted 
            playsInline 
            poster="https://images.unsplash.com/photo-1451187580459-43490279c0fa?q=80&w=2072&auto=format&fit=crop"
          >
            <source id="video-source" src={video1} type="video/mp4" />
          </video>
          {/* Atmospheric Dark Vignette Overlay */}
          <div className="absolute inset-0 bg-gradient-to-t from-black/85 via-black/35 to-black/50 pointer-events-none"></div>
          
          {/* Top-Left Branding / SATQUERY Wordmark */}
          <div className="relative z-10 flex items-center gap-2.5">
            <div className="w-8 h-8 rounded-lg bg-blue-600 flex items-center justify-center shadow-lg shadow-blue-500/30">
              <span className="material-symbols-outlined text-white text-[19px]">satellite_alt</span>
            </div>
            <span className="font-bold text-lg tracking-wider text-white font-mono uppercase">SATQUERY</span>
          </div>
          
          {/* Bottom-Left Narrative / Value Statement */}
          <div className="relative z-10 text-white max-w-lg mb-12 lg:mb-16 ml-2 lg:ml-4">
            <div className="flex items-center gap-2 mb-3">
              <span className="inline-block w-8 h-[2px] bg-blue-500"></span>
            </div>
            <h1 className="font-bold text-3xl lg:text-4xl tracking-tight text-white leading-tight mb-2">
             <t> See the Earth differently.</t>
            </h1>
            <p className="text-sm text-slate-300 font-normal leading-relaxed opacity-90">
              <br></br><br></br>
            </p>
          </div>
        </section>

        {/* RIGHT 50%: Clean Minimal Authentication Pane */}
        <section className="w-1/2 h-full bg-white flex flex-col justify-between items-center py-8 px-8 lg:px-16 overflow-y-auto relative">
          
          {/* Top Header Navigation Bar */}
          <div className="w-full flex justify-between items-center h-8">
            <button 
              className={`text-sm font-medium text-slate-500 hover:text-slate-900 flex items-center gap-1.5 transition-colors cursor-pointer py-1 px-2 -ml-2 rounded-md hover:bg-slate-100 ${authState === 'register2' ? 'flex' : 'hidden'}`}
              id="credentials-back-btn" 
              type="button" 
              onClick={() => setAuthState('register1')}
            >
              <span className="material-symbols-outlined text-[18px]">arrow_back</span>
              <span>Back</span>
            </button>
            <div className="ml-auto"></div>
          </div>

          {/* STATE 1: SIGN IN (DEFAULT) */}
          {authState === 'login' && (
            <div className="auth-step flex-col w-full max-w-md mx-auto my-auto py-2 active-step" id="auth-state-login">
              {/* Logo / Heading */}
              <div className="flex flex-col items-center text-center mb-7">
                <h2 className="text-2xl lg:text-3xl font-bold text-slate-900 tracking-tight">Welcome to SATQUERY</h2><br></br>
                <p className="text-sm text-slate-500 mt-1.5">Sign in to continue to your geospatial intelligence workspace.</p><br></br>
              </div>

              {errorMsg && (
                <div className="mb-4 p-3 bg-red-50 border border-red-200 text-red-600 text-sm rounded-lg text-center">
                  {errorMsg}
                </div>
              )}

              {/* JWT Authentication Form */}
              <form autoComplete="on" className="flex flex-col gap-4" id="jwt-login-form" method="POST" onSubmit={handleLoginSubmit}>
                {/* Email or Username Field */}
                <div className="flex flex-col gap-1.5">
                  <label className="text-[11px] font-mono uppercase tracking-wider text-slate-700 font-medium" htmlFor="identifier">
                    Email or Username
                  </label>
                  <div className="relative">
                    <input 
                      autoComplete="username" 
                      className="w-full h-11 px-3.5 rounded-lg bg-white border border-slate-200 text-slate-900 placeholder:text-slate-400 text-sm outline-none transition-all shadow-sm focus:border-black focus:ring-1 focus:ring-black" 
                      id="identifier" 
                      name="identifier" 
                      placeholder="  name@organization.com or username" 
                      required 
                      type="text"
                      value={email}
                      onChange={(e) => setEmail(e.target.value)}
                    />
                  </div>
                </div>

                {/* Password Field */}
                <div className="flex flex-col gap-1.5">
                  <div className="flex items-center justify-between">
                    <label className="text-[11px] font-mono uppercase tracking-wider text-slate-700 font-medium" htmlFor="password">
                      Password
                    </label>
                    <a className="text-xs text-blue-600 hover:text-blue-700 hover:underline cursor-pointer font-medium" href="#" id="forgot-password-link">
                      Forgot password?
                    </a>
                  </div>
                  <div className="relative flex items-center">
                    <input 
                      autoComplete="current-password" 
                      className="w-full h-11 pl-3.5 pr-11 rounded-lg bg-white border border-slate-200 text-slate-900 placeholder:text-slate-400 text-sm outline-none transition-all shadow-sm focus:border-black focus:ring-1 focus:ring-black" 
                      id="password" 
                      name="password" 
                      placeholder="••••••••••••" 
                      required
                      minLength={8}
                      type={showPassword ? 'text' : 'password'}
                      value={password}
                      onChange={(e) => setPassword(e.target.value)}
                    />
                    <button 
                      aria-label="Toggle password visibility" 
                      className="absolute right-2.5 p-1 rounded-md text-slate-400 hover:text-slate-700 flex items-center justify-center transition-colors" 
                      id="toggle-password-btn" 
                      type="button"
                      onClick={() => setShowPassword(!showPassword)}
                    >
                      <span className="material-symbols-outlined text-[20px]" id="password-toggle-icon">
                        {showPassword ? 'visibility_off' : 'visibility'}
                      </span>
                    </button>
                  </div>
                </div>

                {/* Session Controls */}
                <div className="flex items-center justify-between mt-1">
                  <label className="flex items-center gap-2 cursor-pointer select-none">
                    <input className="w-4 h-4 rounded border-slate-300 text-black accent-black cursor-pointer focus:ring-black" id="remember-me" type="checkbox" />
                    <span className="text-xs text-slate-600">Remember device</span>
                  </label>
                  <span className="text-[11px] font-mono text-slate-500 flex items-center gap-1">
                    <span className="material-symbols-outlined text-[13px] text-blue-600">lock</span>
                  </span>
                </div>

                {/* Submit Button */}
                <button disabled={loading} className="w-full h-11 bg-black text-white text-sm font-medium rounded-lg shadow-sm hover:bg-slate-800 active:scale-[0.99] transition-all flex items-center justify-center gap-2 mt-2 cursor-pointer" id="submit-btn" type="submit">
                  {loading ? (
                    <span className="animate-spin h-4 w-4 rounded-full border-2 border-white border-t-transparent" id="submit-spinner"></span>
                  ) : (
                    <>
                      <span id="submit-text">Sign in</span>
                      <span className="material-symbols-outlined text-[18px]">arrow_forward</span>
                    </>
                  )}
                </button>
              </form>
                  <br></br>
              {/* Sign-up Redirect Prompt */}
              <p className="text-sm text-slate-500 mt-6 text-center">
                Don't have an account? 
                    <br></br>
                <button className="font-semibold text-slate-900 hover:underline cursor-pointer ml-1" id="go-to-signup-btn" type="button" onClick={() => setAuthState('register1')}>Create one</button>
              </p>
            </div>
          )}

          {/* STATE 2: SIGN UP - STEP 1 */}
          {authState === 'register1' && (
            <div className="auth-step flex-col w-full max-w-md mx-auto my-auto py-2 active-step" id="auth-state-register-step1">
              <div className="flex items-center justify-center gap-1.5 mb-6">
                <div className="h-1.5 w-6 rounded-full bg-blue-600"></div>
                <div className="h-1.5 w-1.5 rounded-full bg-slate-200"></div>
                <div className="h-1.5 w-1.5 rounded-full bg-slate-200"></div>
              </div>
              <h2 className="text-3xl font-bold text-slate-900 tracking-tight text-center mb-8">Enter your email</h2>
              
              {errorMsg && (
                <div className="mb-4 p-3 bg-red-50 border border-red-200 text-red-600 text-sm rounded-lg text-center">
                  {errorMsg}
                </div>
              )}

              <form className="flex flex-col gap-4" id="register-step1-form" onSubmit={handleRegisterStep1}>
                <div className="flex flex-col gap-1.5">
                  <label className="text-sm text-slate-600 font-medium" htmlFor="reg-email">Email</label>
                  <input 
                    className="w-full h-12 px-4 rounded-xl bg-white border border-blue-600 text-slate-900 placeholder:text-slate-400 text-sm outline-none transition-all shadow-sm focus:ring-2 focus:ring-blue-500/20" 
                    id="reg-email" 
                    name="reg-email" 
                    placeholder="Enter your email to get started" 
                    required 
                    type="email"
                    value={email}
                    onChange={(e) => setEmail(e.target.value)}
                  />
                </div>
                <button className="w-full h-12 bg-black text-white text-base font-semibold rounded-full shadow-sm hover:bg-slate-800 active:scale-[0.99] transition-all flex items-center justify-center mt-2 cursor-pointer" id="email-continue-btn" type="submit">
                  Continue
                </button>
              </form>

              <div className="relative flex py-5 items-center">
                <div className="flex-grow border-t border-slate-200"></div>
                <span className="flex-shrink mx-4 text-xs text-slate-400 lowercase font-medium">or</span>
                <div className="flex-grow border-t border-slate-200"></div>
              </div>

              <p className="text-sm text-slate-500 mt-6 text-center">
                Already have an account? 
                <button className="go-to-signin-btn font-semibold text-blue-600 hover:underline cursor-pointer ml-1" type="button" onClick={() => setAuthState('login')}>Sign in</button>
              </p>
            </div>
          )}

          {/* STATE 3: SIGN UP - STEP 2 */}
          {authState === 'register2' && (
            <div className="auth-step flex-col w-full max-w-md mx-auto my-auto py-2 active-step" id="auth-state-register-step2">
              <div className="flex items-center justify-center gap-1.5 mb-6">
                <div className="h-1.5 w-1.5 rounded-full bg-slate-200"></div>
                <div className="h-1.5 w-6 rounded-full bg-blue-600"></div>
                <div className="h-1.5 w-1.5 rounded-full bg-slate-200"></div>
              </div>
              <h2 className="text-3xl font-bold text-slate-900 tracking-tight text-center mb-7">Setup your credentials</h2>
              
              {errorMsg && (
                <div className="mb-4 p-3 bg-red-50 border border-red-200 text-red-600 text-sm rounded-lg text-center">
                  {errorMsg}
                </div>
              )}

              <form className="flex flex-col gap-4" id="register-step2-form" onSubmit={handleRegisterStep2}>
                <div className="flex flex-col gap-1.5">
                  <label className="text-sm text-slate-600 font-medium" htmlFor="reg-username">Username</label>
                  <input 
                    className="w-full h-12 px-4 rounded-xl bg-white border border-blue-600 text-slate-900 placeholder:text-slate-400 text-sm outline-none transition-all shadow-sm focus:ring-2 focus:ring-blue-500/20" 
                    id="reg-username" 
                    name="username" 
                    placeholder="Choose a username" 
                    required 
                    type="text"
                    value={username}
                    onChange={(e) => setUsername(e.target.value)}
                  />
                </div>
                
                <div className="flex flex-col gap-1.5">
                  <label className="text-sm text-slate-600 font-medium" htmlFor="reg-password">Password</label>
                  <div className="relative flex items-center">
                    <input 
                      className="w-full h-12 pl-4 pr-11 rounded-xl bg-white border border-slate-200 text-slate-900 placeholder:text-slate-400 text-sm outline-none transition-all shadow-sm focus:border-blue-600 focus:ring-1 focus:ring-blue-600" 
                      id="reg-password" 
                      name="password" 
                      placeholder="At least 8 characters" 
                      required
                      minLength={8}
                      type={showRegPassword ? 'text' : 'password'}
                      value={password}
                      onChange={(e) => setPassword(e.target.value)}
                    />
                    <button 
                      aria-label="Toggle password visibility" 
                      className="absolute right-3 p-1 rounded-md text-slate-400 hover:text-slate-700 flex items-center justify-center transition-colors" 
                      id="toggle-reg-password-btn" 
                      type="button"
                      onClick={() => setShowRegPassword(!showRegPassword)}
                    >
                      <span className="material-symbols-outlined text-[20px]" id="reg-password-toggle-icon">
                        {showRegPassword ? 'visibility_off' : 'visibility'}
                      </span>
                    </button>
                  </div>
                </div>

                <div className="flex flex-col gap-1.5">
                  <label className="text-sm text-slate-600 font-medium" htmlFor="reg-confirm-password">Confirm password</label>
                  <div className="relative flex items-center">
                    <input 
                      className="w-full h-12 pl-4 pr-11 rounded-xl bg-white border border-slate-200 text-slate-900 placeholder:text-slate-400 text-sm outline-none transition-all shadow-sm focus:border-blue-600 focus:ring-1 focus:ring-blue-600" 
                      id="reg-confirm-password" 
                      name="confirmPassword" 
                      placeholder="Confirm your password" 
                      required
                      minLength={8}
                      type={showConfirmPassword ? 'text' : 'password'}
                      value={confirmPassword}
                      onChange={(e) => setConfirmPassword(e.target.value)}
                    />
                    <button 
                      aria-label="Toggle password visibility" 
                      className="absolute right-3 p-1 rounded-md text-slate-400 hover:text-slate-700 flex items-center justify-center transition-colors" 
                      id="toggle-reg-confirm-btn" 
                      type="button"
                      onClick={() => setShowConfirmPassword(!showConfirmPassword)}
                    >
                      <span className="material-symbols-outlined text-[20px]" id="reg-confirm-toggle-icon">
                        {showConfirmPassword ? 'visibility_off' : 'visibility'}
                      </span>
                    </button>
                  </div>
                </div>

                <button disabled={loading} className="w-full h-12 bg-black text-white text-base font-semibold rounded-full shadow-sm hover:bg-slate-800 active:scale-[0.99] transition-all flex items-center justify-center gap-2 mt-2 cursor-pointer" id="credentials-submit-btn" type="submit">
                  {loading ? (
                    <span className="animate-spin h-4 w-4 rounded-full border-2 border-white border-t-transparent" id="reg-spinner"></span>
                  ) : (
                    <span id="reg-btn-text">Continue</span>
                  )}
                </button>
              </form>

              <p className="text-sm text-slate-500 mt-6 text-center">
                Already have an account? 
                <button className="go-to-signin-btn font-semibold text-blue-600 hover:underline cursor-pointer ml-1" type="button" onClick={() => setAuthState('login')}>Sign in</button>
              </p>
            </div>
          )}

          {/* Right Column Sub-footer */}
          <div className="w-full flex flex-col items-center text-center gap-1.5 pt-4">
            <p className="text-xs text-slate-500 tracking-normal">
              AI-powered satellite intelligence for a changing planet.
            </p>
            <div className="flex items-center gap-2.5 text-slate-400 font-mono text-[11px]">
              <span>•</span>
              <span>•</span>
            </div>
          </div>

        </section>
      </main>
    </div>
  );
}
