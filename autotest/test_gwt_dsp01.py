import os
import sys
import numpy as np

try:
    import pymake
except:
    msg = 'Error. Pymake package is not available.\n'
    msg += 'Try installing using the following command:\n'
    msg += ' pip install https://github.com/modflowpy/pymake/zipball/master'
    raise Exception(msg)

try:
    import flopy
except:
    msg = 'Error. FloPy package is not available.\n'
    msg += 'Try installing using the following command:\n'
    msg += ' pip install flopy'
    raise Exception(msg)

from framework import testing_framework
from simulation import Simulation

ex = ['dsp01a', 'dsp01b']
xt3d = [False, True]
exdirs = []
for s in ex:
    exdirs.append(os.path.join('temp', s))
ddir = 'data'


def get_model(idx, dir):
    nlay, nrow, ncol = 1, 1, 100
    nper = 1
    perlen = [5.0]
    nstp = [200]
    tsmult = [1.]
    steady = [True]
    delr = 1.
    delc = 1.
    top = 1.
    laytyp = 0
    ss = 0.
    sy = 0.1
    botm = [0.]
    strt = 1.
    hnoflo = 1e30
    hdry = -1e30
    hk = 1.0

    c = {0: [[(0, 0, 0), 0.0000000], [(0, 0, 99), 0.0000000]]}

    nouter, ninner = 100, 300
    hclose, rclose, relax = 1e-6, 1e-6, 1.

    tdis_rc = []
    for i in range(nper):
        tdis_rc.append((perlen[i], nstp[i], tsmult[i]))

    name = ex[idx]

    # build MODFLOW 6 files
    ws = dir
    sim = flopy.mf6.MFSimulation(sim_name=name, version='mf6',
                                 exe_name='mf6',
                                 sim_ws=ws)
    # create tdis package
    tdis = flopy.mf6.ModflowTdis(sim, time_units='DAYS',
                                 nper=nper, perioddata=tdis_rc)

    # create gwf model
    gwfname = 'gwf_' + name
    gwf = flopy.mf6.MFModel(sim, model_type='gwf6', modelname=gwfname,
                            model_nam_file='{}.nam'.format(gwfname))
    gwf.name_file.save_flows = True

    # create iterative model solution and register the gwf model with it
    imsgwf = flopy.mf6.ModflowIms(sim, print_option='SUMMARY',
                                  outer_hclose=hclose,
                                  outer_maximum=nouter,
                                  under_relaxation='NONE',
                                  inner_maximum=ninner,
                                  inner_hclose=hclose, rcloserecord=rclose,
                                  linear_acceleration='CG',
                                  scaling_method='NONE',
                                  reordering_method='NONE',
                                  relaxation_factor=relax,
                                  fname='{}.ims'.format(gwfname))
    sim.register_ims_package(imsgwf, [gwf.name])

    dis = flopy.mf6.ModflowGwfdis(gwf, nlay=nlay, nrow=nrow, ncol=ncol,
                                  delr=delr, delc=delc,
                                  top=top, botm=botm,
                                  idomain=np.ones((nlay, nrow, ncol), dtype=np.int),
                                  fname='{}.dis'.format(gwfname))

    # initial conditions
    ic = flopy.mf6.ModflowGwfic(gwf, strt=strt,
                                fname='{}.ic'.format(gwfname))

    # node property flow
    npf = flopy.mf6.ModflowGwfnpf(gwf,
                                  save_specific_discharge=True,
                                  icelltype=laytyp,
                                  k=hk,
                                  k33=hk)

    # chd files
    chd = flopy.mf6.ModflowGwfchd(gwf, maxbound=len(c),
                                  stress_period_data=c,
                                  save_flows=False,
                                  pname='CHD-1')

    # output control
    oc = flopy.mf6.ModflowGwfoc(gwf,
                                budget_filerecord='{}.cbc'.format(gwfname),
                                head_filerecord='{}.hds'.format(gwfname),
                                headprintrecord=[
                                    ('COLUMNS', 10, 'WIDTH', 15,
                                     'DIGITS', 6, 'GENERAL')],
                                saverecord=[('HEAD', 'LAST'),
                                            ('BUDGET', 'LAST')],
                                printrecord=[('HEAD', 'LAST'),
                                             ('BUDGET', 'LAST')])

    # create gwt model
    gwtname = 'gwt_' + name
    gwt = flopy.mf6.MFModel(sim, model_type='gwt6', modelname=gwtname,
                            model_nam_file='{}.nam'.format(gwtname))
    gwt.name_file.save_flows = True

    # create iterative model solution and register the gwt model with it
    imsgwt = flopy.mf6.ModflowIms(sim, print_option='SUMMARY',
                                  outer_hclose=hclose,
                                  outer_maximum=nouter,
                                  under_relaxation='NONE',
                                  inner_maximum=ninner,
                                  inner_hclose=hclose, rcloserecord=rclose,
                                  linear_acceleration='BICGSTAB',
                                  scaling_method='NONE',
                                  reordering_method='NONE',
                                  relaxation_factor=relax,
                                  fname='{}.ims'.format(gwtname))
    sim.register_ims_package(imsgwt, [gwt.name])

    dis = flopy.mf6.ModflowGwtdis(gwt, nlay=nlay, nrow=nrow, ncol=ncol,
                                  delr=delr, delc=delc,
                                  top=top, botm=botm,
                                  idomain=1,
                                  fname='{}.dis'.format(gwtname))

    # initial conditions
    ic = flopy.mf6.ModflowGwtic(gwt, strt=0.,
                                fname='{}.ic'.format(gwtname))

    # advection
    adv = flopy.mf6.ModflowGwtadv(gwt, scheme='UPSTREAM',
                                fname='{}.adv'.format(gwtname))

    # dispersion
    dsp = flopy.mf6.ModflowGwtdsp(gwt, xt3d=xt3d[idx], diffc=100.,
                                  alh=0., alv=0., ath1=0., atv=0.,
                                  fname='{}.dsp'.format(gwtname))

    # constant concentration
    cncs = {0: [[(0, 0, 0), 1.0]]}
    cnc = flopy.mf6.ModflowGwtcnc(gwt, maxbound=len(cncs),
                                  stress_period_data=cncs,
                                  save_flows=False,
                                  pname='CNC-1')

    # storage
    sto = flopy.mf6.ModflowGwtsto(gwt, porosity=0.1,
                                fname='{}.sto'.format(gwtname))

    # sources
    ssm = flopy.mf6.ModflowGwtssm(gwt, sources=[[]],
                                  fname='{}.ssm'.format(gwtname))

    # output control
    oc = flopy.mf6.ModflowGwtoc(gwt,
                                budget_filerecord='{}.cbc'.format(gwtname),
                                concentration_filerecord='{}.ucn'.format(gwtname),
                                concentrationprintrecord=[
                                    ('COLUMNS', 10, 'WIDTH', 15,
                                     'DIGITS', 6, 'GENERAL')],
                                saverecord=[('CONCENTRATION', 'LAST'),
                                            ('BUDGET', 'LAST')],
                                printrecord=[('CONCENTRATION', 'LAST'),
                                             ('BUDGET', 'LAST')])

    # GWF GWT exchange
    gwfgwt = flopy.mf6.ModflowGwfgwt(sim, exgtype='GWF6-GWT6',
                                     exgmnamea=gwfname, exgmnameb=gwtname,
                                     fname='{}.gwfgwt'.format(name))

    return sim


def build_models():
    for idx, dir in enumerate(exdirs):
        sim = get_model(idx, dir)
        sim.write_simulation()
    return


def eval_transport(sim):
    print('evaluating transport...')

    name = ex[sim.idxsim]
    gwtname = 'gwt_' + name

    fpth = os.path.join(sim.simpath, '{}.ucn'.format(gwtname))
    try:
        cobj = flopy.utils.HeadFile(fpth, precision='double',
                                    text='CONCENTRATION')
        conc = cobj.get_data()
    except:
        assert False, 'could not load data from "{}"'.format(fpth)

    # This is the answer to this problem.  These concentrations are for
    # time step 200.
    cres = [[[ 1.        , 0.97472443, 0.94947431, 0.92427504, 0.89915185,
               0.87412972, 0.84923335, 0.82448706, 0.79991471, 0.77553964,
               0.75138462, 0.72747174, 0.70382241, 0.68045725, 0.65739608,
               0.63465784, 0.61226053, 0.59022124, 0.56855604, 0.54727998,
               0.52640705, 0.50595018, 0.4859212 , 0.46633085, 0.44718873,
               0.42850336, 0.41028211, 0.39253126, 0.37525599, 0.35846038,
               0.34214746, 0.32631921, 0.31097658, 0.29611954, 0.28174707,
               0.26785727, 0.2544473 , 0.24151351, 0.22905142, 0.21705579,
               0.20552066, 0.19443937, 0.18380466, 0.17360869, 0.16384304,
               0.15449886, 0.14556682, 0.13703721, 0.12889996, 0.12114473,
               0.1137609 , 0.10673763, 0.10006394, 0.09372869, 0.08772068,
               0.08202862, 0.07664126, 0.07154731, 0.06673558, 0.06219493,
               0.05791434, 0.05388294, 0.05009   , 0.04652499, 0.04317758,
               0.04003765, 0.03709534, 0.03434103, 0.03176537, 0.0293593 ,
               0.02711402, 0.02502107, 0.02307224, 0.02125967, 0.01957579,
               0.01801336, 0.01656542, 0.01522538, 0.01398691, 0.01284404,
               0.01179109, 0.01082267, 0.00993375, 0.00911954, 0.0083756 ,
               0.00769775, 0.00708212, 0.00652511, 0.00602341, 0.00557398,
               0.00517407, 0.00482116, 0.00451303, 0.0042477 , 0.00402344,
               0.00383879, 0.00369253, 0.00358368, 0.00351152, 0.00347556]]]
    cres = np.array(cres)
    assert np.allclose(cres, conc), 'simulated concentrations do not match with known solution.'

    return


# - No need to change any code below
def test_mf6model():
    # initialize testing framework
    test = testing_framework()

    # build the models
    build_models()

    # run the test models
    for idx, dir in enumerate(exdirs):
        yield test.run_mf6, Simulation(dir, exfunc=eval_transport, idxsim=idx)

    return


def main():
    # initialize testing framework
    test = testing_framework()

    # build the models
    build_models()

    # run the test models
    for idx, dir in enumerate(exdirs):
        sim = Simulation(dir, exfunc=eval_transport, idxsim=idx)
        test.run_mf6(sim)

    return


if __name__ == "__main__":
    # print message
    print('standalone run of {}'.format(os.path.basename(__file__)))

    # run main routine
    main()
