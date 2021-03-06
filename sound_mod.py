import glob
import matplotlib.pyplot as plt
import numpy as np
import pandas as pd
import scipy.io
# from scipy.io.matlab.mio import savemat
import torch
import torch.nn as nn
from torch.utils.data import Dataset
from torch.utils.data import DataLoader
import streamlit as st
import scipy.integrate
from scipy.io import wavfile, loadmat
import math
from scipy.io.wavfile import write
from PIL import Image

from config import path_dataset, path_model
from feature_extractor import FeatureExtractor
from sound_generator import SoundGenerator


is_cuda = torch.cuda.is_available()
device = torch.device('cuda' if is_cuda else 'cpu')

st.set_page_config(layout="wide")
st.markdown("<h1 style='text-align: center;'>Sound Modification App</h1>", unsafe_allow_html=True)
st.markdown("<h1 style='text-align: center;'>Made by James Fleming and Bradley Goedde</h1>", unsafe_allow_html=True)
st.title('')
st.title('')
# st.title('')
# st.header('Welcome to the Sound Modification App')
# st.text('In this app, the goal is to take your piano audio file as an input and using feature engineering transform it to a guitar sound!')
# st.text('Follow the steps below for how to use the app!')
# st.text('') 
# st.header('Steps to use Synthesizer')
# st.text('1. Upload your piano key audio file (ex: A4.wav). You can hear the audio file you uploaded by pressing the play button on the audio bar. ')
# st.text('2. Below, the steps that are used to complete the sound transformation are displayed.')
# st.text('3. Click on the "see explanation" box to the right of each step to see an explanation of how the step works!')
# st.text('4. Scroll to the bottom of the page to see the final guitar sound generated from your input piano key.')
# st.text('5. Press the play button on the audio bar to hear the generated guitar sound! Hopefully this app has given you a greater understanding of how feature engineering works!')
# st.text('')
# st.text('')
st.set_option('deprecation.showPyplotGlobalUse', False)

first_left, input_file, first_right                = st.beta_columns([3, 7, 3])
a, input_graph, input_graph_desc, a2               = st.beta_columns([1, 7, 4, 1])
third_left, input_play_button, third_right         = st.beta_columns([3, 7, 3])
b, FFT_graph, FFT_desc, b2                         = st.beta_columns([1, 7, 4, 1])
c, STFT_graph, STFT_desc, c2                       = st.beta_columns([1, 7, 4, 1])
d, feat_graph, feat_graph_desc, d2                 = st.beta_columns([1, 8, 3, 1])
e, feat_table, feat_table_desc, e2                 = st.beta_columns([1, 7, 4, 1])
f, guitar_gen_graph, gen_graph_desc, f2            = st.beta_columns([1, 7, 4, 1])
g, guitar_gen_audio, gen_audio_desc, g2            = st.beta_columns([1, 7, 4, 1])
h, TTLS_title, TTLS_other, h2                      = st.beta_columns([1, 7, 4, 1])
TTLS_padding_left, TTLS_image, TTLS_padding_right  = st.beta_columns([3, 7, 3])
TTLS_real_piano, TTLS_real_guitar, TTLS_gen_guitar = st.beta_columns([1, 1, 1])

# Grabbing sound file data
def get_user_data() -> bool:
    with input_file: 
        # st.markdown('### You can download piano sound files from these links:')
        str_1 = "[A4](https://drive.google.com/file/d/1M3DsuEWyni7nriWUEDYV5Bm0cHouzIGu/view?usp=sharing)"
        str_2 = "[B5](https://drive.google.com/file/d/1kKuqvcnndprUlUk7HJYcNDXMY0lUN6AQ/view?usp=sharing)"
        str_3 = "[C5](https://drive.google.com/file/d/1VaMwbizezrByfnT3VJO5CtuEHBUFg1t7/view?usp=sharing)"
        str_4 = "[D5](https://drive.google.com/file/d/1rFn41-4MXXiGD2YyAJVvdOUBIFsm6U-S/view?usp=sharing)"
        st.markdown('### You can download piano sound files from these links: {}, {}, {}, {}'.format(str_1, str_2, str_3, str_4))
        uploaded_file = st.file_uploader('Choose a sound file', accept_multiple_files=False)

    if uploaded_file:
        global key
        with input_play_button: 
            st.text('')
            st.text('')
            st.text('')
            st.text('')
            st.audio(uploaded_file)

        file = uploaded_file.name
        key = file.replace('.wav', '')
        
        FeatureExtractor(uploaded_file, key, input_graph, FFT_graph, STFT_graph)

        return True
    # else:
    #     file = 'A4.wav'
    #     key = file.replace('.wav', '')
        
    #     FeatureExtractor(uploaded_file, key, input_graph, FFT_graph, STFT_graph)
    #     return True
        
    return False


class MyDataset(Dataset):

    """Dataset for MDS method"""

    def __init__(self, path_dataset, data_type):
        super(MyDataset, self).__init__()
        self.feat_list = ['freq_out', 'phi_out', 'a_out', 'b_out']

        # TODO: make the files paths universal to access github files
        if data_type == 'train':
            # self.piano_list = glob.glob(glob.escape(f'{dataset_path}/piano/train/**/*.mat'))
            # self.piano_list = glob.glob(r'https://github.com/mhe314/Research/tree/master/piano/train/*.mat')
            self.piano_list = [r'piano/train/{}.mat'.format(key)]

            # self.piano_list = glob.glob('/**/*.mat', recursive=True)
        else:
            # self.piano_list = glob.glob(f'**/*{dataset_path}/piano/test/**/*.mat')
            # self.piano_list = glob.glob(r'https://github.com/mhe314/Research/tree/master/piano/test/*.mat')

            # self.piano_list = glob.glob(glob.escape('/piano/test/*.mat'))
            self.piano_list = [r'piano/test/{}.mat'.format(key)]
            # self.piano_list = glob.glob('/**/*.mat', recursive=True)

        self.guitar_list = self.parse_guitar_list()


        # without normalization
        self.feats_all_p = self.wrap_data(self.piano_list)  # all piano features
        self.feats_all_g = self.wrap_data(self.guitar_list)
        # print('no norm', self.feats_all_p[0][0, :])

        # normalization
        self.parse_minmax_p()
        self.parse_minmax_g()
        self.feats_all_p_norm = self.normalize_p()
        self.feats_all_g_norm = self.normalize_g()

    def parse_guitar_list(self):
        """Parse guitar_list"""
        guitar_list = []
        for piano_path in self.piano_list:
            guitar_path = piano_path.replace('piano', 'guitar')
            guitar_list.append(guitar_path)
        return guitar_list

    def merge_feats(self, mat_data):
        """merge 4 features into 1 feature"""
        freq = mat_data['omega'].reshape(1, -1)
        phi = mat_data['phi']
        a = mat_data['a']
        b = mat_data['b']
        feats_all = np.concatenate([freq, phi, a, b], axis=0)
        return feats_all

    def wrap_data(self, file_list):
        """add all features into an array"""
        feats_all = np.zeros((len(self.piano_list), 4, 8))  # for each feats: 4*8 dimension
        for idx, file_path in enumerate(file_list):
            feats = self.merge_feats(scipy.io.loadmat(file_path))
            feats_all[idx, :, :] = feats
        return feats_all

    def parse_minmax_p(self):
        """parse minmax for piano data"""
        self.freq_max_p, self.freq_min_p = 8424.0, 440.0
        self.phi_max_p, self.phi_min_p = 1.0, 0.0
        self.a_max_p, self.a_min_p = 0.34, 0
        self.b_max_p, self.b_min_p = -2, -17
        return None

    def parse_minmax_g(self):
        """parse minmax for guitar data"""
        self.freq_max_g, self.freq_min_g = 8424.0, 440.0
        self.phi_max_g, self.phi_min_g = 1.0, 0.0
        self.a_max_g, self.a_min_g = 0.23, 0
        self.b_max_g, self.b_min_g = -1.1, -12
        return None

    def normalize_p(self):
        """normalize piano data"""
        norm_all = np.zeros((len(self.piano_list), 4, 8))
        norm_all[:, 0, :] = (self.feats_all_p[:, 0, :] - self.freq_min_p) / (self.freq_max_p - self.freq_min_p)
        norm_all[:, 1, :] = (self.feats_all_p[:, 1, :] - self.phi_min_p) / (self.phi_max_p - self.phi_min_p)
        norm_all[:, 2, :] = (self.feats_all_p[:, 2, :] - self.a_min_p) / (self.a_max_p - self.a_min_p)
        norm_all[:, 3, :] = (self.feats_all_p[:, 3, :] - self.b_min_p) / (self.b_max_p - self.b_min_p)
        return norm_all

    def normalize_g(self):
        """normalize guitar data"""
        norm_all = np.zeros((len(self.piano_list), 4, 8))
        norm_all[:, 0, :] = (self.feats_all_g[:, 0, :] - self.freq_min_g) / (self.freq_max_g - self.freq_min_g)
        norm_all[:, 1, :] = (self.feats_all_g[:, 1, :] - self.phi_min_g) / (self.phi_max_g - self.phi_min_g)
        norm_all[:, 2, :] = (self.feats_all_g[:, 2, :] - self.a_min_g) / (self.a_max_g - self.a_min_g)
        norm_all[:, 3, :] = (self.feats_all_g[:, 3, :] - self.b_min_g) / (self.b_max_g - self.b_min_g)
        return norm_all

    def inverse_piano(self, feats_each):
        """inverse to original range for piano"""
        feats_orig = np.zeros((4, 8))
        feats_orig[0, :] = feats_each[0, :] * (self.freq_max_p - self.freq_min_p) + self.freq_min_p
        feats_orig[1, :] = feats_each[1, :] * (self.phi_max_p - self.phi_min_p) + self.phi_min_p
        feats_orig[2, :] = feats_each[2, :] * (self.a_max_p - self.a_min_p) + self.a_min_p
        feats_orig[3, :] = feats_each[3, :] * (self.b_max_p - self.b_min_p) + self.b_min_p
        return feats_orig

    def inverse_guitar(self, feats_each):
        """inverse to original range for guitar"""
        feats_orig = np.zeros((4, 8))
        feats_orig[0, :] = feats_each[0, :] * (self.freq_max_g - self.freq_min_g) + self.freq_min_g
        feats_orig[1, :] = feats_each[1, :] * (self.phi_max_g - self.phi_min_g) + self.phi_min_g
        feats_orig[2, :] = feats_each[2, :] * (self.a_max_g - self.a_min_g) + self.a_min_g
        feats_orig[3, :] = feats_each[3, :] * (self.b_max_g - self.b_min_g) + self.b_min_g
        return feats_orig

    def __len__(self):
        return len(self.piano_list)

    def __getitem__(self, idx):
        if torch.is_tensor(idx):
            idx = idx.tolist()

        piano_path = self.piano_list[idx]       # piano sound path
        key_name = piano_path.split('/')[-1].split('.')[0]  # this get the key name from the file
        piano_feats = self.feats_all_p_norm[idx]
        guitar_feats = self.feats_all_g_norm[idx]

        return piano_feats.astype(np.float32), guitar_feats.astype(np.float32), key_name


class SimpleNet(nn.Module):

    """ This is your FFNN model """

    def __init__(self, input_dim, output_dim):
        """
        input_dim: input dimension
        output_dim: output dimension
        """
        super(SimpleNet, self).__init__()
        self.fc1 = nn.Linear(input_dim, 100)
        self.fc2 = nn.Linear(100, 100)
        self.fc3 = nn.Linear(100, 100)
        self.fc4 = nn.Linear(100, output_dim)

    def forward(self, inputs):
        """Net forward"""
        x = torch.tanh(self.fc1(inputs))
        x = torch.tanh(self.fc2(x))
        x = torch.tanh(self.fc3(x))
        x = self.fc4(x)
        return x


class Configer:
    
    """ Parameters for training """
    epoch = 5000
    batch_size = 4
    lr = 0.001
    p_length = 8
    g_length = 8

    def __init__(self):
        super(Configer, self).__init__()


def guitar_feature_generator(path_dataset, key_name, plot: bool = True):
    """Generate predicted guitar features from piano features

    Args:
        dataset_path: [String] folder to save dataset, please name it as "dataset";
        key_name: [String] key name that you want to generate. Example: "A4"

    Returns:
        gen_guitar_feats: [List] contains predicted guitar features in a dict,
                            note that this part can be used to generate many guitar features,
                            so we use a list to store the guitar features.
    """
    config = Configer()
    net = SimpleNet(config.p_length, config.g_length)
    net.to(device)
    net.load_state_dict(torch.load(path_model, map_location=torch.device('cpu')))
    net.eval()

    dataset_train = MyDataset(path_dataset, 'train')
    train_loader = DataLoader(dataset_train, batch_size=config.batch_size, shuffle=True)

    for step, (inputs, targets, key_names) in enumerate(train_loader):
        inputs = inputs.to(device)
        targets = targets.to(device)
        inputs = inputs.reshape(inputs.shape[0], 4, -1)
        targets = targets.reshape(inputs.shape[0], 4, -1)
        outputs = net(inputs)

        gen_feats_batch = outputs.detach().cpu().numpy()
        targets_batch = targets.detach().cpu().numpy()
        inputs_batch = inputs.detach().cpu().numpy()

        for i in range(gen_feats_batch.shape[0]):
            if key_names[i] != key_name:
                st.title(('key name[i]:', key_names[i], 'key name:', key_name))
                continue

            pred_feats_norm = gen_feats_batch[i].reshape(4, 8)

            # inverse data to original range
            pred_feats = dataset_train.inverse_guitar(pred_feats_norm)
            #st.title(pred_feats[0, :3])
            #scipy.io.savemat('A4_generated.mat', pred_feats)
            true_feats_norm = targets_batch[i].reshape(4, 8)
            true_feats = dataset_train.inverse_guitar(true_feats_norm)
            #st.title(true_feats[0, :3])
            inputs_feats_norm = inputs_batch[i].reshape(4, 8)
            inputs_feats = dataset_train.inverse_piano(inputs_feats_norm)

            d = {
                'Key': key_names[i],
                'omega': pred_feats[0, :],
                'phi': pred_feats[1, :],
                'a': pred_feats[2, :],
                'b': pred_feats[3, :],
            }
            d_true = {
                'Key': key_names[i],
                'Frequency [Hz]': true_feats[0, :],
                'Phi [radians]': true_feats[1, :],
                'Amplitude (a)': true_feats[2, :],
                'Damping Coefficient (b)': true_feats[3, :],
            }

            # x_limit = d_true['Frequency [Hz]'][7] + 500

            # plot results
            if plot:
                #st.title('About to plot')  # Title for streamlit app
                fig = plt.figure(figsize=(12, 5))
                # st.pyplot(fig)
                ax1 = fig.add_subplot(1, 2, 1)
                lns1 = plt.plot(pred_feats[0, :], pred_feats[2, :], '^', label='Prediction (G)')
                lns2 = plt.plot(true_feats[0, :], true_feats[2, :], 'v', label='Ground Truth (G)')
                plt.xlabel('Frequency [Hz]', fontsize=16)
                plt.ylabel('Amplitude, a', fontsize=16)
                ax2 = ax1.twinx()
                lns3 = plt.plot(inputs_feats[0, :], inputs_feats[2, :], 'o', c='g', label='Ground Truth (P)')
                lns = lns1 + lns2 + lns3
                labs = [l.get_label() for l in lns]
                ax1.legend(lns, labs, loc=0, fontsize=14)
                plt.title('Key: ' + key_names[i], fontsize=18)

                ax3 = fig.add_subplot(1, 2, 2)
                lns1 = plt.plot(pred_feats[1, :], pred_feats[3, :], '^', label='Prediction (G)')
                lns2 = plt.plot(true_feats[1, :], true_feats[3, :], 'v', label='Ground Truth (G)')
                plt.xlabel('Phase Angle [radians]', fontsize=16)
                plt.ylabel('Damping Coefficient, $b_i$', fontsize=16)
                ax4 = ax3.twinx()
                lns3 = plt.plot(inputs_feats[1, :], inputs_feats[3, :], 'o', c='g', label='Ground Truth (P)')
                lns = lns1 + lns2 + lns3
                labs = [l.get_label() for l in lns]
                ax3.legend(lns, labs, loc=0, fontsize=14)
                plt.title('Key: ' + key_names[i], fontsize=18)

                plt.tight_layout()
                
                #st.pyplot()
                #st.title('Plotted')  # Title for streamlit app

                # plt.savefig(f'results/MDS_pred_{key_names[i]}.jpg', doi=300)

            return d


if get_user_data():

    with input_graph_desc:
        st.text('')
        st.text('')
        st.text('')
        st.text('')
        SignalBox = st.beta_expander(label='Inputted Piano note')
        with SignalBox:
            """
            <fill this in>
            """

    with FFT_desc:
        st.text('')
        st.text('')
        st.text('')
        st.text('')
        FFTbox = st.beta_expander(label='Fast Fourier Transform note')
        with FFTbox: 
            """
            Here is the Fast Fourier Transform graph. By using sin waves, FFT makes it easier to see the dominant frequency and its harmonics. 
            These frequenices are collected and will be used as the "frequency feature" and the amplitudes for these frequencies are collected and will be used as the "a feature".
            Then using a simple wave equation, the phase angle can be collected and used as the "phi feature".
            These important features will be used later on to process the signal using the neural network.
            """

    with STFT_desc:    
        st.text('')
        st.text('')
        st.text('')
        st.text('')
        STFTbox = st.beta_expander(label='Short Time Fourier Transform note')
        with STFTbox:
            """
            Similarly to the Fast Fourier Transform above, the Short Time Fourier Transform graph here uses sin waves to gather important information from the signal.
            Using a heat map and time on the x-axis, we can see how the damping coefficient changes with frequency. 
            The darker the color the larger the damping coefficient (the more negative).
            """

    gen_guitar_feats = guitar_feature_generator(path_dataset, key)
    
    # with feat_graph:
    #     st.title('Features comparison')
    #     st.pyplot()

    with feat_graph_desc:  
        st.text('')
        st.text('')
        st.text('')
        st.text('')  
        # FPlot = st.beta_expander(label='Features plot note')
        # with FPlot: 
        #     """
        #     Here we have a plot that compares the generated guitar features with the real sound featuers. 
        #     The predicted guitar features are compared with the real piano features and the real guitar features. 
        #     From this overlay, it is clear that the neural network has been trained well, and the features generated are very close to what they should be!
        #     """

    # with feat_table: 
    #     st.title('Generated guitar features')
    #     del gen_guitar_feats['Key']
    #     savemat("piano/generate/{}_generated.mat".format(key), gen_guitar_feats)
    #     st.header("Key: {}".format(key))

    #     gen_guitar_feats["Frequency"] = gen_guitar_feats["omega"]
    #     del gen_guitar_feats["omega"]

    #     gen_guitar_feats["Phase angle"] = gen_guitar_feats["phi"]
    #     del gen_guitar_feats["phi"]

    #     gen_guitar_feats["Amplitude"] = gen_guitar_feats["a"]
    #     del gen_guitar_feats["a"]

    #     gen_guitar_feats["Damping Coefficient"] = gen_guitar_feats["b"]
    #     del gen_guitar_feats["b"]
    
    #     st.table(gen_guitar_feats)

    with feat_table_desc:
        st.text('')
        st.text('')
        st.text('')
        st.text('')    
        # FTable = st.beta_expander(label='Features table note')
        # with FTable: 
        #     """
        #     Here are the resulting guitar features!
        #     Once the 4 features displayed in the table were collected from the original audio input using FFT and STFT above, they were passed through a neural network which transformed the features the predicted guitar features displayed in the table.
        #     """


    with guitar_gen_audio:
        st.title('Generated guitar audio')
        SoundGenerator("piano/train/{}.mat".format(key), "piano/generate/{}_generated.mat".format(key))
        st.audio("piano/generate/{}_generated.wav".format(key))

    with gen_audio_desc: 
        st.text('')
        st.text('')
        st.text('')
        st.text('')   
        GAudio = st.beta_expander(label='Generated guitar audio note')
        with GAudio: 
            """
            Yay! We've generated a guitar sound! After uploading your piano key, going through feature extraction, 
            then using the neural network to generate the predicted guitar features, these features are used to finally produce the generated guitar audio.
            """

    # get data about guitar signal
    Fs_guitar, sound_data_guitar = wavfile.read("piano/generate/{}_generated.wav".format(key))
    duration = len(sound_data_guitar) / Fs_guitar
    time_guitar = np.arange(0, duration, 1/Fs_guitar)

    with guitar_gen_graph:
        st.title('Generated guitar signal')
        fig = plt.figure()
        plt.plot(time_guitar, sound_data_guitar)
        plt.xlabel('Time [s]')
        plt.ylabel('Amplitude')
        plt.title('{}.wav'.format(key))
        st.pyplot(fig)
    
    with gen_graph_desc:
        st.text('')
        st.text('')
        st.text('')
        st.text('')  
        FPlot = st.beta_expander(label='Generated guitar note')
        with FPlot: 
            """
            <fill this in>
            """
    
    with TTLS_title:
        st.title('')
        st.title("Twinkle Twinkle Little Neural Network")

    with TTLS_image:
        image = Image.open("MDS-process.png")
        st.image(image)

    with TTLS_real_piano:
        st.title("Authentic piano")
        st.audio("TTLS/TTLS-real_piano.wav")

    with TTLS_real_guitar:
        st.title("Authentic guitar")
        st.audio("TTLS/TTLS-real_guitar.wav")

    with TTLS_gen_guitar:
        st.title("Generated guitar")
        st.audio("TTLS/TTLS-gen_guitar.wav")


# def model_trainer(path_dataset):
#     '''train model
    
#     Args:
#         dataset_path: [String] folder to save dataset, please name it as "dataset";

#     Returns:
#         None, but save model to current_folder + "results/mode.pkl"
#     '''
#     # configeration
#     config = Configer()

#     dataset_train = MyDataset(path_dataset, 'train')
#     dataset_test = MyDataset(path_dataset, 'test')
#     print(f'[DATASET] The number of paired data (train): {len(dataset_train)}')
#     print(f'[DATASET] The number of paired data (test): {len(dataset_test)}')
#     print(f'[DATASET] Piano_shape: {dataset_train[0][0].shape}, guitar_shape: {dataset_train[0][1].shape}')

#     # dataset
#     train_loader = DataLoader(dataset_train, batch_size=config.batch_size, shuffle=True)
#     test_loader = DataLoader(dataset_test, batch_size=config.batch_size, shuffle=True)

#     net = SimpleNet(config.p_length, config.g_length)
#     net.to(device)
#     criterion = nn.MSELoss()
#     optimizer = optim.Adam(net.parameters(), lr=config.lr)
#     scheduler = StepLR(optimizer, step_size=int(config.epoch/4.), gamma=0.3)

#     # Note that this part is about model_trainer
#     loss_list = []
#     for epoch_idx in range(config.epoch):
#         # train
#         for step, (piano_sound, guitar_sound, _) in enumerate(train_loader):
#             inputs = piano_sound.to(device)
#             targets = guitar_sound.to(device)
#             inputs = inputs.reshape(inputs.shape[0], 4, -1)
#             targets = targets.reshape(inputs.shape[0], 4, -1)

#             optimizer.zero_grad()
#             outputs = net(inputs)
#             loss = criterion(outputs, targets)
#             loss_list.append(loss.item())
#             loss.backward()
#             optimizer.step()

#         # eval
#         if epoch_idx % int(config.epoch/10.) == 0:
#             net.eval()
#             for step, (inputs, targets, _) in enumerate(train_loader):
#                 inputs = inputs.to(device)
#                 targets = targets.to(device)
#                 inputs = inputs.reshape(inputs.shape[0], 4, -1)
#                 targets = targets.reshape(inputs.shape[0], 4, -1)
#                 outputs = net(inputs)
#             loss = criterion(outputs, targets)
#             print(f'epoch: {epoch_idx}/{config.epoch}, loss: {loss.item()}')

#     # save model
#     torch.save(net.state_dict(), path_dataset.replace('dataset', 'results')+'/model.pkl')

#     # plot loss history
#     fig = plt.figure()
#     plt.plot(loss_list, 'k')
#     plt.ylim([0, 0.02])
#     plt.xlabel('Iteration', fontsize=16)
#     plt.ylabel('Loss', fontsize=16)
#     plt.tight_layout()
#     st.pyplot()
#     #plt.savefig('results-MDS/MDS_loss.jpg', doi=300)

# model_trainer(path_dataset)
