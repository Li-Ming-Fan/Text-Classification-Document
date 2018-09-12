#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
Created on Tue Sep 11 06:56:44 2018

@author: limingfan
"""

import tensorflow as tf

from zoo_layers import rnn_layer
from zoo_layers import att_pool_layer
from zoo_layers import gather_and_pad_layer


def build_graph(config):
    
    input_x = tf.placeholder(tf.int32, [None, None], name='input_x')
    input_n = tf.placeholder(tf.int32, [None], name='input_n')
    input_y = tf.placeholder(tf.int64, [None], name='input_y')

    with tf.device('/cpu:0'):
        emb_mat = tf.get_variable('embedding',
                                  [config.vocab.size(), config.vocab.emb_dim],
                                  initializer=tf.constant_initializer(config.vocab.embeddings),
                                  trainable = config.emb_tune)
        seq_emb = tf.nn.embedding_lookup(emb_mat, input_x)
        
        seq_mask = tf.cast(tf.cast(input_x, dtype = tf.bool), dtype = tf.int32)
        seq_len = tf.reduce_sum(seq_mask, 1)

    with tf.name_scope("rnn"):
        
        seq_e = rnn_layer(seq_emb, seq_len, 128, config.keep_prob,
                          activation = tf.nn.relu, concat = True, scope = 'bi-lstm-1')   
        B = tf.shape(seq_e)[0]
        query = tf.get_variable("query", [config.att_dim],
                                initializer = tf.ones_initializer())
        query = tf.tile(tf.expand_dims(query, 0), [B, 1])
        feat_s = att_pool_layer(seq_e, query, seq_mask, config.att_dim,
                                config.keep_prob, is_train=None, scope="att_pooling")        
        #feat = seq_e[:,-1,:]
        
        #feat_m = tf.reduce_max(feat_s, reduction_indices=[1], name='feat_m')
        
        #
        feat_g, mask_s = gather_and_pad_layer(feat_s, input_n)
        
        #
        seq_e = rnn_layer(feat_g, input_n, 128, config.keep_prob,
                          activation = tf.nn.relu, concat = True, scope = 'bi-lstm-2')
        B = tf.shape(seq_e)[0]
        query = tf.get_variable("query_s", [config.att_dim],
                                initializer = tf.ones_initializer())
        query = tf.tile(tf.expand_dims(query, 0), [B, 1])
        feat = att_pool_layer(seq_e, query, mask_s, config.att_dim,
                              config.keep_prob, is_train=None, scope="att_pooling_s")


    with tf.name_scope("score"):
        #
        fc = tf.contrib.layers.dropout(feat, config.keep_prob)
        fc = tf.layers.dense(fc, 128, name='fc1')            
        fc = tf.nn.relu(fc)
        
        fc = tf.contrib.layers.dropout(fc, config.keep_prob)
        logits = tf.layers.dense(fc, config.num_classes, name='fc2')
        # logits = tf.nn.sigmoid(fc)
        
        normed_logits = tf.nn.softmax(logits, name='logits')          
        y_pred_cls = tf.argmax(logits, 1, name='pred_cls')
        
    with tf.name_scope("loss"):
        #
        cross_entropy = tf.nn.sparse_softmax_cross_entropy_with_logits(logits = logits,
                                                                       labels = input_y)
        loss = tf.reduce_mean(cross_entropy, name = 'loss')

    with tf.name_scope("accuracy"):
        #
        correct_pred = tf.equal(input_y, y_pred_cls)
        acc = tf.reduce_mean(tf.cast(correct_pred, tf.float32), name = 'metric')
    
    #
    print(normed_logits)
    print(acc)
    print(loss)
    print()
    #

