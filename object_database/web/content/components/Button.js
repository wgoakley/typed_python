/**
 * Button Cell Component
 */

import {Component} from './Component';
import {h} from 'maquette';

/**
 * About Replacements
 * ------------------
 * This component has one regular replacement:
 * `contents`
 */

/**
 * About Named Children
 * ---------------------
 * `content` (single) - The cell inside of the button (if any)
 */
class Button extends Component {
    constructor(props, ...args){
        super(props, ...args);

        // Bind context to methods
        this.makeContent = this.makeContent.bind(this);
        this._getEvents = this._getEvent.bind(this);
        this._getHTMLClasses = this._getHTMLClasses.bind(this);
    }

    render(){
        return(
            h('button', {
                id: this.props.id,
                "data-cell-id": this.props.id,
                "data-cell-type": "Button",
                class: this._getHTMLClasses(),
                onclick: this._getEvent('onclick')
            }, [this.makeContent()]
             )
        );
    }

    makeContent(){
        if(this.usesReplacements){
            return this.getReplacementElementFor('contents');
        } else {
            return this.renderChildNamed('content');
        }
    }

    _getEvent(eventName) {
        return this.props.extraData.events[eventName];
    }

    _getHTMLClasses(){
        let classString = this.props.extraData.classes.join(" ");
        // remember to trim the class string due to a maquette bug
        return classString.trim();
    }
}

export {Button, Button as default};
