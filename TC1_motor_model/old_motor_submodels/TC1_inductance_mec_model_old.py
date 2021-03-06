import numpy as np
import matplotlib.pyplot as plt

from csdl import Model, ScipyKrylov, NewtonSolver
import csdl
from csdl_om import Simulator

class InductanceQImplicitModel(Model):
    def initialize(self):
        self.parameters.declare('pole_pairs') # 6
        self.parameters.declare('phases') # 3
        self.parameters.declare('num_slots') # 36
        self.parameters.declare('fit_coeff_dep_H') # FITTING COEFFICIENTS (X = H, B = f(H))
        self.parameters.declare('fit_coeff_dep_B') # FITTING COEFFICIENTS (X = B, H = g(B))

    def fitting_dep_H(self, H):
        f = self.fit_coeff_dep_H[0] * csdl.tanh(H/300 - 0.25) + 0.4
        return f

    def fitting_dep_B(self, B):
        a = self.fit_coeff_dep_B[0]
        b = self.fit_coeff_dep_B[1]
        c = self.fit_coeff_dep_B[2]
        f = (a*csdl.exp(b*B + c) + 200) * B**1.4
        return f

    def define(self):
        m = self.parameters['phases']
        p = self.parameters['pole_pairs']
        Z = self.parameters['num_slots']
        self.fit_coeff_dep_H = self.parameters['fit_coeff_dep_H']
        self.fit_coeff_dep_B = self.parameters['fit_coeff_dep_B']
        
        phi_aq = self.declare_variable('phi_aq') # STATE

        alpha_i = self.declare_variable('alpha_i')
        pole_pitch = self.declare_variable('pole_pitch')
        l_ef = self.declare_variable('l_ef')
        B_aq = phi_aq/(alpha_i*pole_pitch*l_ef)

        K_theta = self.declare_variable('K_theta')
        air_gap_depth = self.declare_variable('air_gap_depth')
        mu_0 = np.pi*4e-7
        F_sigma_q = 1.6*B_aq*(K_theta*air_gap_depth)/mu_0

        tooth_pitch = self.declare_variable('tooth_pitch')
        tooth_width = self.declare_variable('tooth_width')
        kfe = 0.95 # LAMINATION COEFFICIENT

        B_t_q = B_aq*tooth_pitch*l_ef/tooth_width/kfe/l_ef
        H_t1_q = self.fitting_dep_B(B_t_q)
        h_slot = self.declare_variable('slot_height')
        F_t1_q = 2*H_t1_q*h_slot # DIFF OF MAGNETIC POTENTIAL ALONG TOOTH

        h_ys = self.declare_variable('height_yoke_stator')
        B_j1_q = phi_aq/(2*l_ef*h_ys)
        H_j1_q = self.fitting_dep_B(B_j1_q)

        Kaq = self.declare_variable('Kaq')
        Kdp1 = self.declare_variable('Kdp1')
        turns_per_phase = self.declare_variable('turns_per_phase')
        L_j1 = self.declare_variable('L_j1')
        F_j1_q = 2*H_j1_q*L_j1
        F_total_q = F_sigma_q + F_t1_q + F_j1_q # TOTAL MAGNETIC STRENGTH ON Q-AXIS
        I_q_temp = self.register_output(
            'I_q_temp',
            p*F_total_q/(0.9*m*Kaq*Kdp1*turns_per_phase)
         ) #  CURRENT AT Q-AXIS
        I_d_temp = self.declare_variable('I_d_temp')
        I_w = self.declare_variable('I_w')

        inductance_residual = self.register_output(
            'inductance_residual',
            I_d_temp**2 + I_q_temp**2 - I_w**2
        )

class InductanceModel(Model):
    def initialize(self):
        self.parameters.declare('pole_pairs') # 6
        self.parameters.declare('phases') # 3
        self.parameters.declare('num_slots') # 36
        self.parameters.declare('fit_coeff_dep_H') # FITTING COEFFICIENTS (X = H, B = f(H))
        self.parameters.declare('fit_coeff_dep_B') # FITTING COEFFICIENTS (X = B, H = g(B))

    def fitting_dep_H_old(self, H):
        f = []
        order = 10
        for i in range(order + 1):
            f.append(self.fit_coeff_dep_H[i] * H**(order-i))
        return csdl.sum(*f)
    ''' FOR LOOP MIGHT BE A PROBLEM BECAUSE OBJECT H IS BEING APPENDED TO A NORMAL PYTHON LIST '''
    
    def fitting_dep_H(self, H):
        f = self.fit_coeff_dep_H[0] * csdl.tanh(H/300 - 0.25) + 0.4
        return f

    def fitting_dep_B(self, B):
        a = self.fit_coeff_dep_B[0]
        b = self.fit_coeff_dep_B[1]
        c = self.fit_coeff_dep_B[2]
        f = (a*csdl.exp(b*B + c) + 200) * B**1.4
        return f

    def define(self):
        m = self.parameters['phases']
        p = self.parameters['pole_pairs']
        Z = self.parameters['num_slots']
        self.fit_coeff_dep_H = self.parameters['fit_coeff_dep_H']
        self.fit_coeff_dep_B = self.parameters['fit_coeff_dep_B']

        # --- d-axis inductance ---
        phi_air = self.declare_variable('phi_air')
        F_total = self.declare_variable('F_total')
        F_delta = self.declare_variable('F_delta')
        f_i = self.declare_variable('f_i')
        mu_0 = np.pi*4e-7
        l_ef = self.declare_variable('l_ef')
        kdp1 = self.declare_variable('kdp1')
        W_1 = self.declare_variable('turns_per_phase')

        K_st = F_total/F_delta
        Cx = (4*np.pi*f_i*mu_0*l_ef*(kdp1*W_1)**2) / p

        h_k = 0.0008 # NOT SURE HWAT THIS IS
        h_os = 1.5 * h_k # NOT SURE WHAT THIS IS
        b_sb = self.declare_variable('slot_bottom_width')
        b_s1 = self.declare_variable('slot_width_inner')

        lambda_U1 = (h_k/b_sb) + (2*h_os/(b_sb+b_s1))
        lambda_L1 = 0.45
        lambda_S1 = lambda_U1 + lambda_L1

        Kdp1 = self.declare_variable('Kdp1')

        X_s1 = (2*p*m*l_ef*lambda_S1*Cx)/(l_ef*Z*Kdp1**2)

        s_total = 0.0128
        pole_pitch = self.declare_variable('pole_pitch')
        air_gap_depth = self.declare_variable('air_gap_depth')
        K_theta = self.declare_variable('K_theta')

        X_d1 = (m*pole_pitch*s_total*Cx) / (air_gap_depth*K_theta*K_st*(np.pi*Kdp1)**2)

        l_B = l_ef + 2*0.01 # straight length of coil
        Tau_y = self.declare_variable('Tau_y')

        X_E1 = 0.47*Cx*(l_B - 0.64*Tau_y)/(l_ef*Kdp1**2)
        X_1 = X_s1+X_d1+X_E1

        Kf = self.declare_variable('Kf')
        Kad = self.register_output('Kad', 1/Kf)
        Kaq = self.register_output('Kaq', 0.36/Kf)

        I_w = self.declare_variable('I_w')
        I_d_temp = I_w/2
        turns_per_phase = self.declare_variable('turns_per_phase')
        F_ad = 0.45*m*Kad*Kdp1*turns_per_phase*I_d_temp/p
        hm = 0.004 # MAGNET THICKNESS
        Hc = 907000 # MAGNET COERCIVITY
        K_sigma_air = self.declare_variable('K_sigma_air') # COEFFICIENT OF LEAKAGE IN AIR GAP

        f_a = F_ad / (K_sigma_air*hm*Hc)

        lambda_n = self.declare_variable('lambda_n')
        lambda_leak_standard = self.declare_variable('lambda_leak_standard')
        Am_r = self.declare_variable('Am_r')
        Br = 1.2 # MAGNET REMANENCE
        K_phi = self.declare_variable('K_phi')
        E_o = 4.44*f_i*Kdp1*turns_per_phase*phi_air*K_phi
        bm_N = (lambda_n*(1-f_a)) / (lambda_n + 1) # lambda_n comes from MEC
        phi_air_N = (bm_N*(1-bm_N)*lambda_leak_standard) * Am_r * Br
        E_d = 4.44*f_i*Kdp1*turns_per_phase*phi_air_N*K_phi # EM at d-axis
        Xad  = ((E_o-E_d)**2)**0.5/I_d_temp
        Xd = Xad + X_1
        Ld = self.register_output(
            'L_d',
            Xd / (2*np.pi*f_i)
        ) # d-axis inductance

        # --- q-axis inductance (implicit operation) ---
        model = Model()
        phi_aq = model.declare_variable('phi_aq') # STATE

        alpha_i = model.declare_variable('alpha_i')
        pole_pitch = model.declare_variable('pole_pitch')
        l_ef = model.declare_variable('l_ef')
        B_aq = phi_aq/(alpha_i*pole_pitch*l_ef)

        K_theta = model.declare_variable('K_theta')
        air_gap_depth = model.declare_variable('air_gap_depth')
        mu_0 = np.pi*4e-7
        F_sigma_q = 1.6*B_aq*(K_theta*air_gap_depth)/mu_0

        tooth_pitch = model.declare_variable('tooth_pitch')
        tooth_width = model.declare_variable('tooth_width')
        kfe = 0.95 # LAMINATION COEFFICIENT

        B_t_q = B_aq*tooth_pitch*l_ef/tooth_width/kfe/l_ef
        H_t1_q = self.fitting_dep_B(B_t_q)
        h_slot = model.declare_variable('slot_height')
        F_t1_q = 2*H_t1_q*h_slot # DIFF OF MAGNETIC POTENTIAL ALONG TOOTH

        h_ys = model.declare_variable('height_yoke_stator')
        B_j1_q = phi_aq/(2*l_ef*h_ys)
        H_j1_q = self.fitting_dep_B(B_j1_q)

        L_j1 = model.declare_variable('L_j1')
        F_j1_q = 2*H_j1_q*L_j1
        F_total_q = F_sigma_q + F_t1_q + F_j1_q # TOTAL MAGNETIC STRENGTH ON Q-AXIS
        I_q_temp = model.register_output(
            'I_q_temp',
            p*F_total_q/(0.9*m*Kaq*Kdp1*turns_per_phase)
         ) #  CURRENT AT Q-AXIS
        I_d_temp = model.declare_variable('I_d_temp')
        I_w = model.declare_variable('I_w')

        inductance_residual = model.register_output(
            'inductance_residual',
            I_d_temp**2 + I_q_temp**2 - I_w**2
        )

        eps = 1e-5
        phi_air_bracket = self.declare_variable('phi_air') # DECLARING FOR BRACKET
        Inductance_MEC = self.create_implicit_operation(model)
        Inductance_MEC.declare_state('phi_aq', residual='inductance_residual', bracket=(eps, phi_air_bracket - eps))
        Inductance_MEC.nonlinear_solver = NewtonSolver(
            solve_subsystems=False,
            maxiter=100,
            iprint=True
        )

        Inductance_MEC.linear_solver = ScipyKrylov()

        alpha_i = self.declare_variable('alpha_i')
        pole_pitch = self.declare_variable('pole_pitch')
        l_ef = self.declare_variable('l_ef')
        K_theta = self.declare_variable('K_theta')
        air_gap_depth = self.declare_variable('air_gap_depth')
        mu_0 = self.declare_variable('mu_0')
        tooth_pitch = self.declare_variable('tooth_pitch')
        tooth_width = self.declare_variable('tooth_width')
        h_slot = self.declare_variable('slot_height')
        h_ys = self.declare_variable('height_yoke_stator')
        L_j1 = self.declare_variable('L_j1')
        I_d_temp = self.declare_variable('I_d_temp')
        I_w = self.declare_variable('I_w')
        
        phi_aq = Inductance_MEC(
            alpha_i, pole_pitch, l_ef,  K_theta, air_gap_depth, mu_0,
            tooth_pitch, tooth_width, h_slot, h_ys, L_j1,
            I_d_temp, I_w,
        )

        E_aq = phi_aq*E_o/phi_air # EMF @ Q-AXIS
        I_q_temp = self.declare_variable('I_q_temp')
        Xaq = E_aq/I_q_temp
        Xq = Xaq + X_1
        Lq = self.register_output(
            'Lq',
            Xq/(2*np.pi*f_i)
        )









