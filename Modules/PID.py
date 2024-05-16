from datetime import datetime

class PIDFilter:
    def __init__(self, p, i ,d, lowpass_tau, set_point):
        '''
        PID filter. Takes the filter coefficients for the
        proportional, integral and derivative components


        '''
        self.d = d
        self.i = i
        self.p = p
        self.lowpass_tau = lowpass_tau
        self.setPoint = set_point
        self.reset()

    def filter(self, t_in):
        '''
        Calculates filter output given current input. Keeps track of time
        elapsed between subsequent calls and adjusts coefficients accordingly
        '''
        now = datetime.now()
        if self.lastcall:
            dt = (now - self.lastcall).total_seconds() # Get time elapsed since last filter run
        else:
            dt = 0                # If first call, use dt = 0 (proportional filter will checl on this)
        self.lastcall = datetime.now()

        # Calculate PID filter output and update internal counters
        err = self.setPoint - t_in
        self.integ += dt*err*self.i
        if self.integ < 0:
            self.integ = 0
        if dt > 0:
            if self.lastErr is None:
                self.lastErr = err
            deriv = self.d / dt * (err - self.lastErr)
            filter = min( dt/self.lowpass_tau, 1)
            self.lastErr =  filter * err + (1-filter) * self.lastErr #lowpass filter on error, to avoid quantization on derivative
        else:
            deriv = 0

        out = self.p * err + self.integ + deriv
        if out < 0:
            out = 0

        #print(err, self.lastErr, self.integ, deriv)

        #print("Filter %f %f %f %f %f" % (err, out, self.integ, self.lastErr, dt))
        return out

    def reset(self):
        self.integ = 0
        self.lastErr = None
        self.lastcall = None

